"""
对话调度器 — 多 Agent 协调入口

以对话 Agent 作为系统唯一入口，通过意图识别路由到各专业 Agent，
所有 Agent 共享 KV 缓存池，最终产出综合报告。
"""
from __future__ import annotations
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Awaitable

from article_check.agents.base import AgentRole, AgentMessage, BaseAgent
from article_check.core.kvpool import SharedKVPool
from article_check.documents.core import (
    InternalDoc, read_document, write_document, convert_document,
    DocReader, DocWriter, DocumentFormat,
)
from article_check.agents.reporter import AnalysisReport, ReportGenerator

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """多 Agent 共享上下文"""
    doc: Optional[InternalDoc] = None
    paper_path: str = ""
    report: Optional[AnalysisReport] = None
    messages: List[Dict] = field(default_factory=list)


class DialogueAgent:
    """
    对话调度器 — 以对话作为系统唯一入口

    工作流:
      1. 用户输入 → DialogueAgent 识别意图
      2. 路由到对应 Agent
      3. Agent 通过 SharedKVPool 共享上下文
      4. 所有结果汇聚到 ReportGenerator
      5. 输出综合报告

    对话示例:
      "帮我看看这篇论文 paper.docx" → 读文档 → 格式检查 → 文献分析 → 报告
      "文献搜索一下 emotion recognition" → 文献搜索 → 引文分析 → 综述
      "这篇投IEEE能不能过" → 投稿检查
      "帮我改一下格式" → 格式修正
    """

    def __init__(self):
        self.kv_pool = SharedKVPool()
        self.reporter = ReportGenerator()
        self.ctx = AgentContext()
        self._agents: Dict[AgentRole, BaseAgent] = {}
        self._intent_handlers: Dict[str, Callable] = {}
        self._register_intents()
        logger.info("DialogueAgent 初始化完成")

    def _register_intents(self):
        """注册意图到处理函数"""
        self._intent_handlers = {
            "review": self._handle_review,           # 审查
            "format": self._handle_format,           # 格式检查
            "fix": self._handle_fix,                 # 格式修正
            "literature": self._handle_literature,   # 文献搜索
            "survey": self._handle_survey,           # 综述
            "citation": self._handle_citation,       # 引文分析
            "submission": self._handle_submission,   # 投稿检查
            "convert": self._handle_convert,         # 格式转换
            "report": self._handle_report,           # 生成报告
        }

    def register_agent(self, role: AgentRole, agent: BaseAgent):
        self._agents[role] = agent
        logger.info(f"Agent 注册: {role.value}")

    # ─── 意图识别 ──────────────────────────────────────

    def detect(self, text: str) -> tuple:
        """识别用户意图"""
        t = text.lower().strip()

        if t in ("q", "quit", "exit", "退出"):
            return ("exit", "")

        if any(kw in t for kw in ["格式", "format", "版面", "排版"]):
            return ("format", self._extract_path(text))

        if any(kw in t for kw in ["改成", "改格式", "修正", "fix", "对齐"]):
            return ("fix", self._extract_path(text))

        if any(kw in t for kw in ["文献", "搜索", "search", "查一下", "literature"]):
            return ("literature", self._extract_query(text))

        if any(kw in t for kw in ["综述", "survey", "研究现状", "领域"]):
            return ("survey", self._extract_query(text))

        if any(kw in t for kw in ["引文", "引用网络", "citation", "共引", "被引"]):
            return ("citation", self._extract_path(text))

        if any(kw in t for kw in ["投稿", "submission", "检查能不能", "能过", "期刊"]):
            return ("submission", self._extract_path(text))

        if any(kw in t for kw in ["转换", "convert", "转成", "导出"]):
            return ("convert", self._extract_path(text))

        if any(kw in t for kw in ["报告", "report", "汇总", "生成"]):
            return ("report", "")

        # 默认: 审查
        path = self._extract_path(text)
        if path:
            return ("review", path)
        return ("review", text)

    def _extract_path(self, text: str) -> str:
        import re
        m = re.search(r'["\']([^"\']+)["\']', text)
        if m: return m.group(1)
        m = re.search(r'([\w\\/.-]+\.(?:docx|tex|pdf|md|doc|ltx))', text)
        if m: return m.group(1)
        return self.ctx.paper_path

    def _extract_query(self, text: str) -> str:
        import re
        m = re.search(r'["\']([^"\']+)["\']', text)
        if m: return m.group(1)
        m = re.search(r'(?:搜索|查|survey|search)\s*(.+?)(?:论文|文献|的|$)', text)
        if m: return m.group(1).strip()
        return text.strip()[:50]

    # ─── 主循环 ────────────────────────────────────────

    async def run(self, user_input: str) -> Dict[str, Any]:
        """处理用户输入，返回结果"""
        intent, param = self.detect(user_input)

        if intent == "exit":
            return {"type": "exit", "message": "再见!"}

        handler = self._intent_handlers.get(intent)
        if not handler:
            return {"type": "error", "message": f"未识别的意图: {intent}"}

        try:
            result = await handler(param)
            return result
        except Exception as e:
            logger.error(f"处理失败: {e}", exc_info=True)
            return {"type": "error", "message": f"处理失败: {e}"}

    # ─── 处理函数 ──────────────────────────────────────

    async def _handle_review(self, path: str) -> Dict:
        """全流程审查: 读文档 → 格式 → 文献 → 报告"""
        if not path:
            return {"type": "ask", "message": "请提供论文路径"}

        p = Path(path)
        if not p.exists():
            # 尝试扩展名
            for ext in [".docx", ".tex", ".pdf", ".md"]:
                if Path(path + ext).exists():
                    p = Path(path + ext)
                    break
            else:
                return {"type": "error", "message": f"文件不存在: {path}"}

        self.ctx.paper_path = str(p)
        self.ctx.doc = read_document(str(p))

        # 缓存文档内容供其他 Agent 共享
        doc_key = self.kv_pool.put(self.ctx.doc.raw_text[:10000], key=f"doc:{p.stem}")
        meta_key = self.kv_pool.put(json.dumps(self.ctx.doc.to_dict()), key=f"meta:{p.stem}")
        self.kv_pool.acquire(doc_key, "dialogue")
        self.kv_pool.acquire(meta_key, "dialogue")

        # 格式检查
        from article_check.mcp.tools.format_tools import check_docx_format, check_latex_format, check_structure
        from article_check.utils.file_utils import detect_file_type
        ft = detect_file_type(p)
        issues = []
        if ft == "docx":
            issues = check_docx_format(str(p))
        elif ft == "latex":
            issues = check_latex_format(str(p))
        struct = check_structure(file_path=str(p), file_type=ft)

        # 文献提取
        from article_check.references import ReferenceEngine
        re_eng = ReferenceEngine()
        refs = re_eng.extract_from_paper(str(p))
        ref_result = re_eng.validate(str(p), refs)

        # 文献检索
        from article_check.literature import LiteratureSearcher
        searcher = LiteratureSearcher()
        query = self.ctx.doc.metadata.get("title", p.stem)
        papers = await searcher.parallel_search(query, limit_per_source=5)

        # 引文分析
        from article_check.literature import CitationAnalyzer
        analyzer = CitationAnalyzer()
        citation = await analyzer.analyze_references(
            [r.doi for r in refs if r.doi][:5],
            [r.title for r in refs[:5]],
        )

        # 投稿检查
        from article_check.checkers import SubmissionChecker
        from article_check.rules.registry import template_registry
        tpl = template_registry.detect_matching_template()
        tpl_name = tpl.name if tpl else "IEEE Transactions"
        sub = SubmissionChecker(tpl_name).check(str(p))

        # 生成报告
        report = await self.reporter.generate(
            doc=self.ctx.doc,
            format_issues=issues,
            refs=refs,
            literature_papers=[{"title": p.title, "authors": p.authors, "year": p.year} for p in papers[:10]],
            survey_result=None,
            submission_result={"ready": sub.ready, "passed": sub.passed, "total": sub.total, "items": [
                {"name": i.name, "status": i.status} for i in sub.items
            ]},
            citation_analysis_text=citation.field_trend,
            missing_refs=[p.title[:60] for p in citation.missing_references[:5]],
        )

        self.ctx.report = report

        # 保存报告
        report_path = str(Path("reports") / f"{p.stem}_analysis_report.md")
        Path("reports").mkdir(exist_ok=True)
        Path(report_path).write_text(report.to_markdown(), encoding="utf-8")

        # 清理 KV 引用
        self.kv_pool.release(doc_key, "dialogue")
        self.kv_pool.release(meta_key, "dialogue")

        return {
            "type": "review_result",
            "title": report.title,
            "score": report.overall_score,
            "format_issues": len(report.format_issues),
            "format_score": report.format_score,
            "total_refs": report.total_refs,
            "ref_score": report.citation_consistency,
            "literature_found": report.literature_found,
            "submission_ready": sub.ready,
            "submission_passed": f"{sub.passed}/{sub.total}",
            "citation_trend": citation.field_trend,
            "missing_refs": len(report.missing_refs),
            "report_path": report_path,
            "doc_stats": self.ctx.doc.to_dict(),
        }

    async def _handle_format(self, path: str) -> Dict:
        if not path:
            return {"type": "ask", "message": "请提供论文路径"}
        from article_check.mcp.tools.format_tools import check_docx_format, check_latex_format, check_structure
        from article_check.utils.file_utils import detect_file_type
        p = Path(path)
        if not p.exists():
            return {"type": "error", "message": f"文件不存在: {path}"}
        ft = detect_file_type(p)
        issues = []
        if ft == "docx": issues = check_docx_format(str(p))
        elif ft == "latex": issues = check_latex_format(str(p))
        struct = check_structure(file_path=str(p), file_type=ft)
        return {
            "type": "format_result",
            "file_type": ft,
            "issues_count": len(issues),
            "issues": issues,
            "structure": struct.get("found_sections", []),
        }

    async def _handle_fix(self, path: str) -> Dict:
        if not path:
            return {"type": "ask", "message": "请提供论文路径"}
        from article_check.fixers import DocxAutoFixer
        from article_check.mcp.tools.format_tools import check_docx_format
        p = Path(path)
        if not p.exists():
            return {"type": "error", "message": f"文件不存在: {path}"}
        issues = check_docx_format(str(p))
        if not issues:
            return {"type": "fix_result", "message": "无需修正，格式正确", "fixes": []}
        fixer = DocxAutoFixer()
        fixes = fixer.apply(str(p), issues)
        return {"type": "fix_result", "fixes": fixes, "count": len(fixes)}

    async def _handle_literature(self, query: str) -> Dict:
        from article_check.literature import LiteratureSearcher
        searcher = LiteratureSearcher()
        papers = await searcher.parallel_search(query or "deep learning", limit_per_source=8)
        return {
            "type": "literature_result",
            "query": query,
            "count": len(papers),
            "papers": [{"title": p.title[:60], "authors": p.authors[:2], "year": p.year, "doi": p.doi, "source": p.source} for p in papers[:15]],
        }

    async def _handle_survey(self, query: str) -> Dict:
        from article_check.literature import SurveyGenerator
        gen = SurveyGenerator()
        survey = await gen.generate(query or "deep learning")
        return {
            "type": "survey_result",
            "sections": [{"title": s.title, "papers_count": len(s.papers)} for s in survey.sections],
            "trends": survey.trends,
            "missing_refs": [{"title": p.title[:60], "year": p.year} for p in survey.missing_refs],
        }

    async def _handle_citation(self, path: str) -> Dict:
        from article_check.references import ReferenceEngine
        from article_check.literature import CitationAnalyzer
        re_eng = ReferenceEngine()
        refs = re_eng.extract_from_paper(path)
        analyzer = CitationAnalyzer()
        analysis = await analyzer.analyze_references(
            [r.doi for r in refs if r.doi][:5],
            [r.title for r in refs[:5]],
        )
        missing = await analyzer.find_missing_references(
            path, [r.title for r in refs[:5]], top_n=5,
        ) if refs else []
        return {
            "type": "citation_result",
            "core_papers": len(analysis.core_papers),
            "trend": analysis.field_trend,
            "missing_refs": [p.title[:60] for p in missing],
        }

    async def _handle_submission(self, path: str) -> Dict:
        if not path:
            return {"type": "ask", "message": "请提供论文路径"}
        from article_check.checkers import SubmissionChecker
        from article_check.rules.registry import template_registry
        tpl = template_registry.detect_matching_template()
        tpl_name = tpl.name if tpl else "IEEE Transactions"
        sub = SubmissionChecker(tpl_name).check(path)
        return {
            "type": "submission_result",
            "journal": tpl_name,
            "ready": sub.ready,
            "passed": sub.passed,
            "total": sub.total,
            "items": [{"name": i.name, "status": i.status, "detail": i.detail, "suggestion": i.suggestion} for i in sub.items],
        }

    async def _handle_convert(self, path: str) -> Dict:
        if not path:
            return {"type": "ask", "message": "请提供源文件路径（如 paper.docx）"}
        p = Path(path)
        if not p.exists():
            return {"type": "error", "message": f"文件不存在: {path}"}
        targets = [".md", ".tex", ".docx", ".pdf"]
        results = []
        doc = read_document(str(p))
        for ext in targets:
            if ext == p.suffix:
                continue
            out = p.with_suffix(ext)
            write_document(doc, str(out))
            results.append(str(out))
        return {"type": "convert_result", "source": str(p), "outputs": results}

    async def _handle_report(self, _: str = "") -> Dict:
        if not self.ctx.report:
            return {"type": "error", "message": "还没有审查数据，请先审查一篇论文"}
        return {
            "type": "report_result",
            "report_markdown": self.ctx.report.to_markdown(),
            "score": self.ctx.report.overall_score,
        }
