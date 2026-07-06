"""
审查 Worker — 负责执行具体的审查工作单元

Worker 是审查流水线的执行单元，每个 Worker 负责一个审查维度：
- FormatWorker: 格式审查
- ContentWorker: 内容质量审查
- ReferenceWorker: 文献真实性审查
- NoveltyWorker: 创新性评估
"""
from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from article_check.config.settings import config
from article_check.core.harness.base import Harness, HarnessContext
from article_check.core.worktree.manager import WorktreeContext
from article_check.pipeline.models import PaperTask, WorkerResult
from article_check.llm.client.deepseek import DeepSeekClient, LLMResponse

logger = logging.getLogger(__name__)


class Worker(ABC):
    """Worker 基类"""

    def __init__(
        self,
        name: str,
        harness: Optional[Harness] = None,
        llm_client: Optional[DeepSeekClient] = None,
    ):
        self.name = name
        self.harness = harness
        self.llm = llm_client or DeepSeekClient()

    @abstractmethod
    async def work(
        self,
        ctx: WorktreeContext,
        task: PaperTask,
    ) -> WorkerResult:
        """执行审查工作"""
        ...


class FormatWorker(Worker):
    """格式审查 Worker — 混合规则引擎 + LLM 辅助"""

    def __init__(self, harness: Harness):
        super().__init__(name="format_checker", harness=harness)

    async def work(
        self,
        ctx: WorktreeContext,
        task: PaperTask,
    ) -> WorkerResult:
        logger.info(f"[{task.task_id}] FormatWorker 开始")

        issues = []
        file_type = task.file_type or "unknown"

        # 1. 本地规则引擎检查（零 token）
        if file_type == "latex":
            tool = self.harness.get_tool("check_latex_format")
            if tool and tool.fn:
                latex_issues = tool.fn(file_path=str(ctx.paper_copy))
                issues.extend(latex_issues or [])

        elif file_type == "docx":
            tool = self.harness.get_tool("check_docx_format")
            if tool and tool.fn:
                docx_issues = tool.fn(file_path=str(ctx.paper_copy))
                issues.extend(docx_issues or [])

        # 2. 结构完整性检查
        tool = self.harness.get_tool("check_structure")
        if tool and tool.fn:
            struct_issues = tool.fn(
                file_path=str(ctx.paper_copy),
                file_type=file_type,
            )
            if struct_issues:
                issues.extend(struct_issues.get("issues", []))

        score = max(0, 10 - len(issues) * 0.5) / 10
        logger.info(
            f"[{task.task_id}] FormatWorker 完成: "
            f"{len(issues)} issues, score={score}"
        )

        return WorkerResult(
            success=True,
            worker_name=self.name,
            data={"issues": issues, "score": score},
            issues=issues,
            score=score,
        )


class ContentWorker(Worker):
    """内容审查 Worker — 基于 DeepSeek API"""

    def __init__(self, harness: Harness, llm_client: DeepSeekClient):
        super().__init__(
            name="content_reviewer",
            harness=harness,
            llm_client=llm_client,
        )

    async def work(
        self,
        ctx: WorktreeContext,
        task: PaperTask,
    ) -> WorkerResult:
        logger.info(f"[{task.task_id}] ContentWorker 开始")

        # 读取论文内容
        paper_text = ctx.paper_copy.read_text(encoding="utf-8", errors="replace")

        # 结构化输出 schema — 减少 completion tokens
        schema = {
            "type": "object",
            "properties": {
                "strengths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "论文的优点"
                },
                "weaknesses": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "论文的不足"
                },
                "issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "section": {"type": "string"},
                            "type": {"type": "string", "enum": ["logic", "clarity", "completeness", "methodology", "result"]},
                            "severity": {"type": "string", "enum": ["minor", "major", "critical"]},
                            "description": {"type": "string"},
                            "suggestion": {"type": "string"}
                        }
                    }
                },
                "score": {
                    "type": "number",
                    "description": "内容质量评分 0-1"
                },
                "summary": {"type": "string"}
            },
            "required": ["score", "summary", "issues"]
        }

        # 分段审查：避免 40% 上下文阈值问题
        sections = self._split_sections(paper_text)

        all_issues = []
        total_score = 0.0

        for i, section in enumerate(sections):
            if not section["text"].strip():
                continue

            messages = [
                {
                    "role": "system",
                    "content": f"""你是一个学术论文审查专家，负责审查 {section['name']} 部分。
请严格按 JSON Schema 输出，只给出客观、具体的批评意见。"""
                },
                {
                    "role": "user",
                    "content": f"请审查以下论文的 {section['name']} 部分：\n\n{section['text'][:6000]}"
                }
            ]

            try:
                result = self.llm.structured_chat(
                    messages=messages,
                    schema=schema,
                    temperature=0.1,
                )
                all_issues.extend(result.get("issues", []))
                total_score += result.get("score", 0.5)
            except Exception as e:
                logger.error(f"[{task.task_id}] 分段审查失败 ({section['name']}): {e}")

        avg_score = total_score / max(len(sections), 1)
        avg_score = min(1.0, max(0.0, avg_score))

        return WorkerResult(
            success=True,
            worker_name=self.name,
            data={
                "score": avg_score,
                "issues": all_issues,
                "summary": f"审查 {len(sections)} 个章节，发现 {len(all_issues)} 个问题",
            },
            issues=all_issues,
            score=avg_score,
        )

    def _split_sections(self, text: str) -> List[Dict]:
        """将论文分割为段落块（避免超长上下文）"""
        # 简单的分段逻辑
        section_keywords = [
            "abstract", "introduction", "related work",
            "method", "methodology", "experiment", "result",
            "discussion", "conclusion",
            "摘要", "引言", "方法", "实验", "结果", "讨论", "结论"
        ]
        lines = text.split("\n")
        sections = []
        current = {"name": "preamble", "text": ""}

        for line in lines:
            lower = line.lower().strip()
            for kw in section_keywords:
                if kw in lower:
                    if current["text"]:
                        sections.append(current)
                    current = {"name": kw, "text": line + "\n"}
                    break
            else:
                current["text"] += line + "\n"

        if current["text"]:
            sections.append(current)

        return sections


class ReferenceWorker(Worker):
    """文献审查 Worker — 调用学术数据库 API"""

    def __init__(self, harness: Harness):
        super().__init__(name="reference_checker", harness=harness)

    async def work(
        self,
        ctx: WorktreeContext,
        task: PaperTask,
    ) -> WorkerResult:
        logger.info(f"[{task.task_id}] ReferenceWorker 开始")
        # 文献验证逻辑在后续实现
        return WorkerResult(
            success=True,
            worker_name=self.name,
            data={"issues": [], "verified_refs": 0, "score": 1.0},
            score=1.0,
        )
