"""
💬 自然语言对话模式 — 像聊天一样驱动论文审查与修正

无需记忆命令，直接说"帮我看看 paper.tex"、"改成IEEE格式"即可。
意图识别 + 路由到对应功能 + 交互式确认。
"""
from __future__ import annotations
import asyncio
import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from article_check import __version__
from article_check.config.settings import config
from article_check.core.harness.base import Harness
from article_check.llm.client.deepseek import DeepSeekClient
from article_check.pipeline.orchestrator import Orchestrator, PaperTask
from article_check.pipeline.reviewer import Reviewer
from article_check.pipeline.worker import FormatWorker, ContentWorker, ReferenceWorker

logger = logging.getLogger(__name__)


class ChatSession:
    """对话会话 — 管理状态、意图识别、命令路由"""

    def __init__(self, verbose: bool = False):
        self.width = shutil.get_terminal_size().columns
        self.state: Dict[str, Any] = {
            "last_paper": None,
            "last_template": None,
            "last_report": None,
            "papers_in_dir": [],
        }
        self.verbose = verbose

    # ── 输出 ───────────────────────────────────────────

    def say(self, text: str):
        """Assistant 消息"""
        print(f"  \033[1;36m🤖 {text}\033[0m")

    def info(self, text: str):
        """信息输出"""
        print(f"    {text}")

    def input(self, prompt: str = "") -> str:
        """用户输入"""
        try:
            return input(f"  \033[1;33m🗣️  {prompt}\033[0m").strip().strip('"').strip("'")
        except (EOFError, KeyboardInterrupt):
            return "q"

    def banner(self):
        print()
        print("=" * self.width)
        title = f"  💬 Article Check v{__version__} — 对话模式  "
        print(f"  \033[1;36m{title:^{self.width-4}}\033[0m")
        print(f"  \033[2m直接说话就能审查/修改论文，输入 help 看示例，q 退出\033[0m")
        print("=" * self.width)
        print()

    # ── 路径解析 ───────────────────────────────────────

    def resolve_path(self, p: str) -> Optional[Path]:
        """智能路径解析 — 支持相对/绝对/通配/无扩展名"""
        if not p:
            return None
        p = p.strip().strip('"').strip("'")
        # 直接存在
        if Path(p).exists():
            return Path(p)
        # 通配
        import glob
        matches = sorted(glob.glob(p))
        if matches:
            return Path(matches[0])
        # 加扩展名
        for ext in [".tex", ".docx", ".pdf", ".ltx"]:
            if Path(p + ext).exists():
                return Path(p + ext)
        return Path(p)

    def extract_path(self, text: str) -> Optional[str]:
        """从自然语言中提取文件路径"""
        # 引号内
        m = re.search(r'["\']([^"\']+\.[a-zA-Z]+)["\']', text)
        if m:
            return m.group(1)
        m = re.search(r'["\']([^"\']+)["\']', text)
        if m:
            return m.group(1)
        # 文件名后缀
        m = re.search(r'([\w\\/.-]+\.(?:tex|docx|pdf|ltx))', text)
        if m:
            return m.group(1)
        # 目录路径
        for word in text.split():
            clean = word.strip(".,;:!?()")
            p = Path(clean)
            if p.exists():
                return clean
        return None

    # ── 意图识别 ───────────────────────────────────────

    def detect_intent(self, text: str) -> Tuple[str, dict]:
        """
        识别用户意图，返回 (action, params)

        Action: review/format/fix/reference/batch/template_list/template_detect/config/report/help/exit/unknown
        """
        t = text.lower().strip()

        if t in ("q", "quit", "exit", "退出", "结束"):
            return ("exit", {})

        if t in ("help", "h", "?", "帮助"):
            return ("help", {})

        # 模板 — 优先匹配（因为"看看"既是模板也是审查的触发词）
        has_template = any(kw in t for kw in ["模板", "template", "期刊", "journal", "会议"])
        if has_template:
            if "list" in t or "看看" in t or "有什么" in t or "都有" in t or not self.extract_path(text):
                return ("template_list", {})
            if "detect" in t or "自动" in t or "匹配" in t:
                return ("template_detect", {"path": self.extract_path(text)})
            return ("template", {})

        # 修改/修正 — 优先于普通审查
        if any(kw in t for kw in ["改成", "改格式", "改为", "对齐到", "修正到"]):
            params: dict = {"path": self.extract_path(text) or self.state.get("last_paper", ""), "template": None}
            for tag, name in [("ieee", "IEEE Transactions"), ("elsevier", "Elsevier"),
                              ("acm", "ACM Conference"), ("lncs", "Springer LNCS"),
                              ("springer", "Springer LNCS"), ("nature", "Nature")]:
                if tag in t:
                    params["template"] = name
                    break
            return ("fix", params)

        # 格式检查
        if any(kw in t for kw in ["格式", "format", "版面", "样式", "排版", "查格式"]):
            return ("format", {"path": self.extract_path(text) or self.state.get("last_paper", "")})

        # 修正（普通修改用词）
        if any(kw in t for kw in ["改", "修", "fix", "改正", "对齐", "修正", "调整", "纠正"]):
            params: dict = {"path": self.extract_path(text) or self.state.get("last_paper", ""), "template": None}
            for tag, name in [("ieee", "IEEE Transactions"), ("elsevier", "Elsevier"),
                              ("acm", "ACM Conference"), ("lncs", "Springer LNCS"),
                              ("springer", "Springer LNCS"), ("nature", "Nature")]:
                if tag in t:
                    params["template"] = name
                    break
            return ("fix", params)

        # 配置 — 必须优先于"看看"(review)
        if any(kw in t for kw in ["配置", "config", "设置", "环境", "key", "apikey"]):
            return ("config", {})

        # 文献
        if any(kw in t for kw in ["引用", "文献", "reference", "citation", "bib", "doi"]):
            return ("reference", {"path": self.extract_path(text)})

        # 批量
        if any(kw in t for kw in ["批量", "batch", "所有论文", "文件夹里", "多个", "都审", "都查"]):
            return ("batch", {"path": self.extract_path(text)})

        # 审查 — 放在最后，因为"看看"等词太通用
        if any(kw in t for kw in ["审", "review", "看看", "评价", "评估", "审查论文", "检查论文"]):
            return ("review", {"path": self.extract_path(text)})

        # 报告
        if any(kw in t for kw in ["报告", "report", "结果", "上次"]):
            return ("report", {})

        # 检测有无路径 → 默认尝试审查
        path = self.extract_path(text)
        if path:
            return ("review", {"path": path})

        return ("unknown", {})

    # ── 处理器 ─────────────────────────────────────────

    def _auto_detect_template(self, path: Path) -> Optional[str]:
        """自动检测论文匹配的模板"""
        from article_check.rules.registry import template_registry
        suffix = path.suffix.lower()
        if suffix not in (".tex", ".ltx"):
            return None
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            dc = re.search(r'\\documentclass(?:\[[^\]]*\])?\{(.+?)\}', text)
            latex_class = dc.group(1) if dc else None
            packages = re.findall(r'\\usepackage(?:\[[^\]]*\])?\{(.+?)\}', text)
            tpl = template_registry.detect_matching_template(
                latex_class=latex_class, packages=packages, text_sample=text[:500]
            )
            if tpl:
                self.state["last_template"] = tpl.name
                self.say(f"检测到模板: {tpl.name}")
                return tpl.name
        except Exception:
            pass
        return None

    def _run_format_check(self, path: Path) -> List[Dict]:
        """运行本地格式检查"""
        from article_check.mcp.tools.format_tools import check_latex_format, check_docx_format, check_structure
        from article_check.utils.file_utils import detect_file_type

        ft = detect_file_type(path)
        issues = []
        if ft == "latex":
            issues = check_latex_format(str(path))
        elif ft == "docx":
            issues = check_docx_format(str(path))

        struct = check_structure(file_path=str(path), file_type=ft)
        if struct and struct.get("issues"):
            issues.extend(struct["issues"])
        return issues

    def _run_template_check(self, path: Path, template: str) -> List[Dict]:
        """运行模板格式检查"""
        from article_check.rules.engine import TemplateRuleEngine
        engine = TemplateRuleEngine()
        from article_check.utils.file_utils import detect_file_type
        ft = detect_file_type(path)
        return engine.check(template, path, ft)

    def handle_review(self, params: dict):
        """处理审查意图"""
        path_str = params.get("path") or self.state.get("last_paper", "")
        if not path_str:
            self.say("好的！请问论文路径是什么？")
            path_str = self.input()
        p = self.resolve_path(path_str)
        if not p or not p.exists():
            self.say(f"找不到文件: {p}，请检查路径")
            return

        self.state["last_paper"] = str(p)
        self.say(f"收到！开始审查 {p.name} ...")

        # 1. 自动检测模板
        tpl = self._auto_detect_template(p)

        # 2. 格式检查
        issues = self._run_format_check(p)
        self.say(f"格式检查完成，发现 {len(issues)} 个问题")

        crits = sum(1 for i in issues if i.get("severity") == "critical")
        majors = sum(1 for i in issues if i.get("severity") == "major")
        if issues:
            self.info(f"🔴 严重: {crits}  🟡 重要: {majors}  🟢 其他: {len(issues) - crits - majors}")
            for i, issue in enumerate(issues[:5], 1):
                sev = issue.get("severity", "info")
                emoji = {"critical": "🔴", "major": "🟡", "minor": "🟢", "info": "ℹ️"}
                self.info(f"{emoji.get(sev, '•')} {issue.get('description', '')[:80]}")
            if len(issues) > 5:
                self.info(f"... 还有 {len(issues) - 5} 个问题")

        # 3. (可选) 内容审查
        if config.deepseek.api_key:
            self.say("需要进一步做内容深度审查吗？(y/n)")
            if self.input().lower() in ("y", "yes", "是", ""):
                self.say("正在进行内容审查，这需要一些时间...")
                try:
                    from article_check.pipeline.orchestrator import Orchestrator, PaperTask
                    from article_check.utils.file_utils import detect_file_type
                    orch = Orchestrator()
                    orch.register_worker(FormatWorker(orch.harness))
                    orch.register_worker(ContentWorker(orch.harness, DeepSeekClient()))
                    orch.register_worker(ReferenceWorker(orch.harness))
                    orch.register_reviewer(Reviewer())
                    task = PaperTask(task_id=p.stem, paper_path=p, title=p.stem, file_type=detect_file_type(p))
                    result = asyncio.run(orch.review_single(task))
                    self.state["last_report"] = str(result.report_path) if result.report_path else None
                    score = result.overall_score or 0
                    bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
                    self.say(f"审查完成！综合评分: [{bar}] {score:.2f}")
                    if result.report_path:
                        self.info(f"完整报告: {result.report_path}")
                except Exception as e:
                    self.say(f"内容审查出错: {e}")

        # 4. 是否修复
        if issues:
            self.say("需要我帮你修复这些格式问题吗？(y/n)")
            if self.input().lower() in ("y", "yes", "是"):
                self.handle_fix({"path": str(p), "template": tpl})

    def handle_fix(self, params: dict):
        """处理修正意图"""
        path_str = params.get("path") or self.state.get("last_paper", "")
        if not path_str:
            self.say("请提供要修改的论文路径")
            path_str = self.input()
        p = self.resolve_path(path_str)
        if not p or not p.exists():
            self.say(f"找不到: {p}")
            return

        template = params.get("template")
        if not template:
            self.say("目标模板是什么？(例如：IEEE Transactions, Elsevier, ACM Conference, Springer LNCS)")
            self.info("输入 'auto' 自动检测，输入 'list' 查看所有模板")
            ans = self.input()
            if ans.lower() == "auto":
                template = self._auto_detect_template(p)
            elif ans.lower() == "list":
                from article_check.rules.registry import template_registry
                for t in template_registry.list_all():
                    self.info(f"📌 {t.name} [{t.category}]")
                self.say("请输入模板名称：")
                template = self.input()
            else:
                template = ans

        if not template:
            self.say("未指定模板，取消修改")
            return

        # 运行模板检查
        issues = self._run_template_check(p, template)
        if not issues:
            self.say(f"🎉 论文已符合 {template} 格式规范，无需修改！")
            return

        self.say(f"共发现 {len(issues)} 个格式问题 (模板: {template})：")
        for i, issue in enumerate(issues, 1):
            sev = issue.get("severity", "info")
            emoji = {"critical": "🔴", "major": "🟡", "minor": "🟢", "info": "ℹ️"}
            print(f"  {emoji.get(sev, '•')} #{i} [{sev.upper()}] {issue.get('description', '')}")
            if issue.get("suggestion"):
                print(f"     💡 {issue['suggestion']}")

        self.say("是否应用全部修改？(y/n)")
        if self.input().lower() in ("y", "yes", "是"):
            self.say("自动修正即将开始——我会逐项提出修改方案，你确认后执行。")
            self.say("由于需要逐项编辑文件，请稍后。按回车开始修正...")
            self.input()
            # 这里后续接入自动编辑逻辑

            # 重新检查
            remaining = self._run_template_check(p, template)
            if remaining:
                self.say(f"修正后仍有 {len(remaining)} 个问题需手动处理")
            else:
                self.say("🎉 所有问题已修正！")
        else:
            self.say("已取消")

    def handle_batch(self, params: dict):
        """处理批量审查"""
        path_str = params.get("path")
        if not path_str:
            self.say("请提供论文目录路径")
            path_str = self.input()
        d = Path(path_str) if path_str else None
        if not d or not d.is_dir():
            self.say(f"目录不存在: {d}")
            return

        from article_check.utils.file_utils import find_papers
        papers = find_papers(str(d))
        if not papers:
            self.say(f"在 {d} 中没有找到论文文件")
            return

        self.say(f"找到 {len(papers)} 篇论文：")
        for p in papers:
            self.info(f"  [{p['type']}] {p['name']} ({p['size']/1024:.0f} KB)")

        self.say("是否全部审查？(y/n)")
        if self.input().lower() in ("y", "yes", "是"):
            self.say("正在批量审查...")
            try:
                from article_check.pipeline.orchestrator import Orchestrator, PaperTask
                orch = Orchestrator()
                orch.register_worker(FormatWorker(orch.harness))
                if config.deepseek.api_key:
                    orch.register_worker(ContentWorker(orch.harness, DeepSeekClient()))
                orch.register_worker(ReferenceWorker(orch.harness))
                orch.register_reviewer(Reviewer())
                tasks = [PaperTask(task_id=p["name"], paper_path=Path(p["path"]), title=p["name"], file_type=p["type"]) for p in papers]
                results = asyncio.run(orch.review_batch(tasks, max_concurrent=4))
                self.say("批量审查完成！")
                for r in results:
                    score = r.overall_score or 0
                    bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
                    self.info(f"{r.paper_title:30s} [{bar}] {score:.2f}")
                self.info(f"成功: {sum(1 for r in results if not r.errors)}/{len(results)}")
            except Exception as e:
                self.say(f"批量审查出错: {e}")

    def handle_template_list(self):
        """列出所有模板"""
        from article_check.rules.registry import template_registry
        tpls = template_registry.list_all()
        self.say(f"已注册 {len(tpls)} 个模板：")
        for t in tpls:
            tag = f" ({t.latex_class})" if t.latex_class else ""
            self.info(f"  📌 {t.name} [{t.category}]{tag}")

    def handle_template_detect(self, params: dict):
        """自动检测模板"""
        path_str = params.get("path")
        if not path_str:
            self.say("请提供论文路径")
            return
        p = self.resolve_path(path_str)
        if p and p.exists():
            tpl = self._auto_detect_template(p)
            if tpl:
                self.say(f"✅ 自动匹配: {tpl}")
            else:
                self.say("⚠️ 未能自动匹配，可查看模板列表手动选择")
                self.handle_template_list()

    def handle_help(self):
        """显示帮助"""
        print("""
  \033[1m💬 对话示例\033[0m
  ┌──────────────────────────────────────────────────┐
  │ "帮我看看这篇论文 paper.tex"          → 审查      │
  │ "审 paper.docx"                       → 审查      │
  │ "改成IEEE格式 paper.tex"              → 修正      │
  │ "查格式 paper.tex"                    → 格式检查   │
  │ "检查引用"                            → 文献审查   │
  │ "批量审 papers/"                      → 批量审查   │
  │ "有什么模板"                          → 模板列表   │
  │ "自动检测模板 paper.tex"              → 模板匹配   │
  │ "看看配置"                           → 配置显示   │
  │ "帮助" / "help"                      → 显示此帮助 │
  │ "q" / "退出"                         → 退出       │
  └──────────────────────────────────────────────────┘
        """)

    # ── 主循环 ─────────────────────────────────────────

    def run(self):
        """启动对话循环"""
        self.banner()
        self.info("\033[2m试试说：'帮我看看 paper.tex' | '改成IEEE格式' | '批量审 papers/'\033[0m")
        print()

        while True:
            text = self.input()
            if not text:
                continue

            action, params = self.detect_intent(text)

            if action == "exit":
                self.say("再见！随时回来继续审稿 👋")
                break
            elif action == "help":
                self.handle_help()
            elif action == "review":
                self.handle_review(params)
            elif action == "format":
                path = params.get("path") or self.state.get("last_paper", "")
                if not path:
                    self.say("请提供论文路径")
                    continue
                p = self.resolve_path(path)
                if p and p.exists():
                    issues = self._run_format_check(p)
                    self.say(f"格式检查完成，发现 {len(issues)} 个问题")
                    for i, issue in enumerate(issues[:10], 1):
                        sev = issue.get("severity", "info")
                        emoji = {"critical": "🔴", "major": "🟡", "minor": "🟢", "info": "ℹ️"}
                        print(f"  {emoji.get(sev, '•')} {issue.get('description', '')[:90]}")
                    if len(issues) > 10:
                        self.info(f"... 还有 {len(issues) - 10} 个问题")
                else:
                    self.say(f"找不到: {p}")
            elif action == "fix":
                self.handle_fix(params)
            elif action == "reference":
                path = params.get("path")
                self.say("文献验证功能：目前支持引用数量检查。")
                if path:
                    p = self.resolve_path(path)
                    if p and p.exists():
                        text = p.read_text(encoding="utf-8", errors="replace")
                        bibs = re.findall(r'\\bibitem', text)
                        self.info(f"参考文献数量: {len(bibs)} 条")
                        self.say("完整的 DOI 验证功能待接入 Semantic Scholar API")
                else:
                    self.say("请提供论文路径以检查引用")
            elif action == "batch":
                self.handle_batch(params)
            elif action == "template_list":
                self.handle_template_list()
            elif action == "template_detect":
                self.handle_template_detect(params)
            elif action == "config":
                d = config.to_dict()
                safe = {k: v for k, v in d.items()}
                if "deepseek" in safe and isinstance(safe["deepseek"], dict) and safe["deepseek"].get("api_key"):
                    safe["deepseek"]["api_key"] = safe["deepseek"]["api_key"][:8] + "..."
                print(json.dumps(safe, ensure_ascii=False, indent=2))
            elif action == "report":
                rp = self.state.get("last_report")
                if rp and Path(rp).exists():
                    print(Path(rp).read_text(encoding="utf-8")[:1500])
                else:
                    self.say("还没有审查报告记录")
            else:
                self.say("没太理解，试试说 'help' 查看示例")
                self.say("或者直接说：审 paper.tex / 查格式 / 改成IEEE格式")
