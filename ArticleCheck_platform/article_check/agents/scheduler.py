"""
LLM Self-Scheduling Engine — 大模型自我编排引擎

核心理念: 不是用 if-else 规则判断用户意图,
而是让 DeepSeek 自己理解用户需求, 自己决定审查流程。

工作流:
  1. 用户输入自然语言
  2. 发送到 DeepSeek + 可用工具列表
  3. DeepSeek 返回: {intent, plan: [steps], params}
  4. 引擎按照 plan 逐步执行
  5. 每一步都可以让 LLM 再次决策 (self-loop)

优点:
  - 无需硬编码任何意图规则
  - LLM 能理解"帮我看看这篇论文有什么问题"这种模糊表达
  - LLM 能自己编排多步流程
  - 支持未知/未预定义的请求

参考: SelfCompact (arXiv:2606.23525), LLM-as-Scheduler (ACL 2026)
"""
from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Awaitable

from article_check.llm.client.deepseek import DeepSeekClient
from article_check.core.kvpool import SharedKVPool

logger = logging.getLogger(__name__)


# ─── 调度数据结构 ─────────────────────────────────────

@dataclass
class ToolDef:
    """LLM 可调用的工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScheduleStep:
    """调度的一步"""
    action: str           # 工具名或 "think" / "report"
    params: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""   # LLM 为什么选择这一步


@dataclass
class SchedulePlan:
    """LLM 返回的完整计划"""
    intent: str
    reasoning: str        # LLM 对用户需求的理解
    steps: List[ScheduleStep]
    kv_hints: List[str] = field(default_factory=list)  # 建议缓存的 KV key


@dataclass
class ExecutionResult:
    """执行结果"""
    step_results: List[Dict[str, Any]] = field(default_factory=list)
    final_output: Any = None
    token_used: int = 0
    duration: float = 0.0


# ─── 工具注册表 ───────────────────────────────────────

class ToolRegistry:
    """LLM 可调用的工具注册表"""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._defs: Dict[str, ToolDef] = {}

    def register(self, name: str, description: str, fn: Callable, **params):
        self._tools[name] = fn
        self._defs[name] = ToolDef(name=name, description=description, parameters=params)

    def get(self, name: str) -> Optional[Callable]:
        return self._tools.get(name)

    def get_def(self, name: str) -> Optional[ToolDef]:
        return self._defs.get(name)

    def list_tools(self) -> List[Dict]:
        """返回工具列表供 LLM 选择"""
        return [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in self._defs.values()
        ]


# ─── LLM 自我调度引擎 ─────────────────────────────────

SELF_SCHEDULING_SYSTEM_PROMPT = """你是一个学术论文审查系统的调度器。你的任务是根据用户的自然语言输入，规划出最佳的执行计划。

可用工具列表将会在每次请求时提供。

<rules>
1. 理解用户的真实需求，不要逐字匹配关键词
2. 输出必须是 JSON 格式，包含:
   - intent: 简短意图描述（中文）
   - reasoning: 你对用户需求的理解（中文）
   - steps: 执行步骤数组，每步包含 {action, params, reasoning}
   - kv_hints: 建议缓存的上下文键名列表

3. 常见工作流参考:
   - 用户要求审查论文 → [read_document, format_check, extract_refs, search_literature, citation_analysis, generate_report]
   - 用户要求查文献 → [search_literature]
   - 用户要求改格式 → [read_document, format_check, fix_document]
   - 用户要求写综述 → [search_literature, generate_survey]
   - 用户问能否投稿 → [read_document, submission_check]
   - 用户要求格式转换 → [read_document, convert_document]

4. 如果用户需求不明确, 在 reasoning 中说明, 只返回一个 "clarify" 步骤

5. 始终返回纯 JSON, 不要包含其他文本
</rules>"""


class SelfSchedulingEngine:
    """
    LLM 自我调度引擎

    核心流程:
      user_input → LLM(工具列表 + 上下文) → {plan} → 执行 → 结果

    用法:
        engine = SelfSchedulingEngine()
        result = await engine.run("帮我看看这篇论文 paper.docx")
        print(result.final_output)
    """

    def __init__(self, llm_client: Optional[DeepSeekClient] = None):
        self.llm = llm_client or DeepSeekClient()
        self.tools = ToolRegistry()
        self.kv_pool = SharedKVPool()
        self._context: List[Dict] = []   # 对话历史
        self._plan_cache: Dict[str, SchedulePlan] = {}
        logger.info("SelfSchedulingEngine 初始化")

    def register_tool(self, name: str, description: str, fn: Callable, **params):
        """注册一个可调度工具"""
        self.tools.register(name, description, fn, **params)

    # ── LLM 计划生成 ──────────────────────────────────

    async def _llm_plan(self, user_input: str) -> SchedulePlan:
        """让 LLM 生成执行计划"""
        tools_desc = self.tools.list_tools()

        messages = [
            {"role": "system", "content": SELF_SCHEDULING_SYSTEM_PROMPT},
            *self._context[-6:],  # 最近 3 轮对话作为上下文
            {"role": "user", "content": json.dumps({
                "user_input": user_input,
                "available_tools": tools_desc,
                "kv_pool_stats": self.kv_pool.stats(),
            }, ensure_ascii=False)},
        ]

        schema = {
            "type": "object",
            "properties": {
                "intent": {"type": "string", "description": "简短意图描述"},
                "reasoning": {"type": "string", "description": "对用户需求的理解"},
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "description": "工具名或 think/report"},
                            "params": {"type": "object"},
                            "reasoning": {"type": "string"},
                        },
                        "required": ["action"],
                    },
                },
                "kv_hints": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["intent", "reasoning", "steps"],
        }

        try:
            result = self.llm.structured_chat(messages, schema=schema, temperature=0.1)
            plan = SchedulePlan(
                intent=result.get("intent", "unknown"),
                reasoning=result.get("reasoning", ""),
                steps=[ScheduleStep(**s) for s in result.get("steps", [])],
                kv_hints=result.get("kv_hints", []),
            )
            logger.info(f"LLM plan: {plan.intent} → {[s.action for s in plan.steps]}")
            return plan
        except Exception as e:
            logger.error(f"LLM 计划失败: {e}")
            # 降级: 如果是文件路径, 尝试审查
            import re
            path = re.search(r'[\w\\/.-]+\.(docx|tex|pdf|md|doc|ltx)', user_input)
            if path:
                return SchedulePlan(
                    intent="审查论文",
                    reasoning=f"LLM 失效, 降级为审查 {path.group()}",
                    steps=[ScheduleStep("read_document", {"path": path.group()}),
                           ScheduleStep("format_check"),
                           ScheduleStep("extract_refs"),
                           ScheduleStep("search_literature"),
                           ScheduleStep("generate_report")],
                )
            return SchedulePlan(
                intent="downgrade",
                reasoning="LLM 失效且无法解析路径",
                steps=[ScheduleStep("unknown")],
            )

    async def run(self, user_input: str) -> ExecutionResult:
        """执行用户请求的完整流程"""
        start = time.time()
        result = ExecutionResult()

        # 1. LLM 生成计划
        plan = await self._llm_plan(user_input)
        logger.info(f"执行计划: {plan.intent} ({' → '.join(s.action for s in plan.steps)})")

        # 2. 缓存提示
        for hint in plan.kv_hints:
            self.kv_pool.put(hint, key=hint)

        # 3. 逐步执行
        step_context = {}
        for step_idx, step in enumerate(plan.steps):
            logger.info(f"  Step {step_idx+1}/{len(plan.steps)}: {step.action}")

            # 特殊步骤
            if step.action == "unknown":
                result.final_output = {"type": "clarify", "message": "请更具体地描述你想做什么"}
                result.duration = time.time() - start
                return result

            if step.action == "think":
                # LLM 思考步骤 — 更新上下文
                step_result = {"type": "think", "content": step.params.get("prompt", "")}
                step_context["_last_think"] = step_result
                result.step_results.append(step_result)
                continue

            if step.action == "generate_report":
                # 特殊处理: 报告生成
                report_result = await self._execute_report(step_context)
                result.final_output = report_result
                result.step_results.append({"type": "report", "data": report_result})
                self._context.append({"role": "assistant", "content": json.dumps(report_result, ensure_ascii=False)[:500]})
                continue

            # 普通工具执行
            tool_fn = self.tools.get(step.action)
            if not tool_fn:
                result.step_results.append({"type": "error", "action": step.action, "error": f"未知工具: {step.action}"})
                continue

            try:
                # 合并参数: 步骤参数 + 上下文中的文件路径 (过滤未定义参数)
                params = dict(step.params)
                if "path" not in params and "path" in step_context:
                    params["path"] = step_context["path"]
                if "query" not in params and "query" in step_context:
                    params["query"] = step_context["query"]

                # 缓存命中检测
                cache_key = f"{step.action}:{json.dumps(params, sort_keys=True)}"
                cached = self.kv_pool.get(cache_key)
                if cached:
                    step_result = {"type": "cache_hit", "action": step.action, "data": json.loads(cached)}
                    logger.info(f"    KV 缓存命中: {step.action}")
                else:
                    # 执行工具 — 只传递工具能接受的参数
                    import inspect
                    sig = inspect.signature(tool_fn)
                    filtered_params = {k: v for k, v in params.items() if k in sig.parameters}
                    step_result_data = await tool_fn(**filtered_params) if asyncio.iscoroutinefunction(tool_fn) else tool_fn(**filtered_params)
                    step_result = {"type": "result", "action": step.action, "data": step_result_data}
                    # 缓存结果
                    if isinstance(step_result_data, (dict, list)):
                        self.kv_pool.put(json.dumps(step_result_data, ensure_ascii=False), key=cache_key)

                step_context[step.action] = step_result_data
                step_context["path"] = step_context.get("path") or params.get("path", "")
                step_context["query"] = step_context.get("query") or params.get("query", "")
                result.step_results.append(step_result)

            except Exception as e:
                logger.error(f"  步骤失败 {step.action}: {e}")
                result.step_results.append({"type": "error", "action": step.action, "error": str(e)})

        # 4. 清理
        self.kv_pool.compress_all()
        result.duration = time.time() - start

        if result.final_output is None:
            result.final_output = self._summarize_results(result.step_results)

        # 记录对话上下文
        self._context.append({"role": "user", "content": user_input[:200]})
        self._context.append({"role": "assistant", "content": json.dumps(result.final_output, ensure_ascii=False)[:500]})
        if len(self._context) > 20:
            self._context = self._context[-20:]

        return result

    async def _execute_report(self, ctx: Dict) -> Dict:
        """从上下文中提取所有结果生成综合报告"""
        from article_check.agents.reporter import ReportGenerator
        from article_check.documents.core import InternalDoc

        reporter = ReportGenerator()
        doc = ctx.get("read_document") or ctx.get("_last_doc") or InternalDoc()

        format_result = ctx.get("format_check", {})
        refs = ctx.get("extract_refs", [])
        literature = ctx.get("search_literature", [])
        submission = ctx.get("submission_check")
        citation = ctx.get("citation_analysis")

        report = await reporter.generate(
            doc=doc,
            format_issues=format_result if isinstance(format_result, list) else format_result.get("issues", []),
            refs=refs,
            literature_papers=literature if isinstance(literature, list) else literature.get("papers", []),
            submission_result=submission,
            citation_analysis_text=citation.get("trend", "") if isinstance(citation, dict) else "",
        )

        import os
        report_dir = "reports"
        os.makedirs(report_dir, exist_ok=True)
        path = f"{report_dir}/self_scheduled_report.md"
        with open(path, "w", encoding="utf-8") as f:
            f.write(report.to_markdown())

        return {
            "type": "report",
            "score": report.overall_score,
            "format_issues": len(report.format_issues),
            "total_refs": report.total_refs,
            "literature_found": report.literature_found,
            "submission_ready": report.submission_ready,
            "citation_trend": report.citation_analysis[:60] if report.citation_analysis else "",
            "report_path": path,
        }

    def _summarize_results(self, results: List[Dict]) -> Dict:
        """汇总所有执行结果为对话友好的格式"""
        summary = {"steps_completed": len(results), "results": {}}
        for r in results:
            if r.get("type") == "error":
                summary["error"] = r.get("error", "")
            elif r.get("action"):
                data = r.get("data", {})
                if isinstance(data, dict):
                    # 扁平化关键字段
                    for key in ["score", "count", "issues_count", "total_refs", "passed", "total"]:
                        if key in data:
                            summary["results"][r["action"]] = data.get(key)
        return summary


import asyncio
