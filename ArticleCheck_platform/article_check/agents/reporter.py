"""
报告生成 Agent — 自动生成综合论文分析报告

输入: InternalDoc + 审查结果 + 文献分析
输出: 结构化 Markdown/HTML/DOCX 报告
"""
from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from article_check.documents.core import InternalDoc, ReferenceData

logger = logging.getLogger(__name__)


@dataclass
class AnalysisReport:
    """完整分析报告"""
    title: str
    generated_at: float = field(default_factory=time.time)

    # 文档信息
    doc_meta: Dict[str, Any] = field(default_factory=dict)
    doc_stats: Dict[str, Any] = field(default_factory=dict)

    # 格式审查
    format_issues: List[Dict] = field(default_factory=list)
    format_score: float = 1.0

    # 文献分析
    total_refs: int = 0
    ref_score: float = 1.0
    doi_missing: List[str] = field(default_factory=list)
    citation_consistency: float = 1.0

    # 文献检索
    literature_found: int = 0
    literature_papers: List[Dict] = field(default_factory=list)

    # 引文分析
    citation_analysis: str = ""
    missing_refs: List[str] = field(default_factory=list)

    # 综述
    survey_sections: List[Dict] = field(default_factory=list)
    survey_trends: List[str] = field(default_factory=list)

    # 投稿检查
    submission_ready: Optional[bool] = None
    submission_report: Optional[Dict] = None

    # 综合评分
    overall_score: float = 0.0

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"# 📋 论文分析报告\n")
        lines.append(f"**论文**: {self.doc_meta.get('title', self.title)}")
        lines.append(f"**作者**: {self.doc_meta.get('author', 'N/A')}")
        lines.append(f"**综合评分**: **{self.overall_score:.2f}**")
        lines.append(f"**生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append("---\n")

        # 1. 文档统计
        lines.append("## 📊 文档统计\n")
        lines.append(f"| 指标 | 值 |")
        lines.append(f"|------|-----|")
        for k, v in self.doc_stats.items():
            lines.append(f"| {k} | {v} |")
        lines.append("")

        # 2. 格式审查
        lines.append("## 📐 格式审查\n")
        score_bar = self._score_bar(self.format_score)
        lines.append(f"**格式评分**: {score_bar} {self.format_score:.2f}\n")
        if self.format_issues:
            for i, issue in enumerate(self.format_issues[:20], 1):
                sev = issue.get("severity", "info")
                emoji = {"critical": "🔴", "major": "🟡", "minor": "🟢", "info": "ℹ️"}
                lines.append(f"{emoji.get(sev, '•')} **#{i}** {issue.get('description', '')}")
                if issue.get("suggestion"):
                    lines.append(f"> 💡 {issue['suggestion']}")
                lines.append("")
        else:
            lines.append("✅ 未发现格式问题\n")

        # 3. 文献分析
        lines.append("## 📚 文献分析\n")
        lines.append(f"| 指标 | 值 |")
        lines.append(f"|------|-----|")
        lines.append(f"| 参考文献数 | {self.total_refs} |")
        lines.append(f"| 一致性评分 | {self.citation_consistency:.2f} |")
        lines.append(f"| DOI 缺失 | {len(self.doi_missing)} |")
        lines.append(f"| 文献检索 | {self.literature_found} 篇 |")
        lines.append("")
        if self.missing_refs:
            lines.append("### ⚠️ 建议补充文献\n")
            for r in self.missing_refs[:5]:
                lines.append(f"- {r}\n")

        # 4. 引文分析
        if self.citation_analysis:
            lines.append(f"## 🔗 引文分析\n{self.citation_analysis}\n")

        # 5. 综述
        if self.survey_sections:
            lines.append("## 📝 文献综述\n")
            if self.survey_trends:
                for t in self.survey_trends:
                    lines.append(f"- {t}\n")
            for sec in self.survey_sections[:5]:
                lines.append(f"### {sec.get('title', '')}\n")
                for p in sec.get("papers", [])[:5]:
                    lines.append(f"- {p.get('authors', '')} — {p.get('title', '')[:50]} ({p.get('year', '')})\n")

        # 6. 投稿检查
        if self.submission_report:
            lines.append("## 📋 投稿就绪检查\n")
            ready = self.submission_report.get("ready", False)
            items = self.submission_report.get("items", [])
            lines.append(f"{'✅ 可投稿' if ready else '❌ 需修改'} ({self.submission_report.get('passed', 0)}/{self.submission_report.get('total', 0)})\n")
            for item in items:
                status = item.get("status", "")
                emoji = {"pass": "✅", "fail": "❌", "warn": "⚠️"}
                lines.append(f"{emoji.get(status, '•')} {item.get('name', '')}\n")

        lines.append("\n---\n")
        lines.append(f"*报告由 ArticleCheck v0.3.0 自动生成*\n")
        return "\n".join(lines)

    def to_html(self) -> str:
        md = self.to_markdown()
        import re
        html = md
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.M)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.M)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.M)
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'^(\|.+\|)$', r'<code>\1</code>', html, flags=re.M)
        html = re.sub(r'\n{2,}', r'</p><p>', html)
        html = f"<html><head><meta charset='utf-8'><title>论文分析报告</title><style>body{{font-family:system-ui;max-width:800px;margin:0 auto;padding:20px;line-height:1.6}}</style></head><body><p>{html}</p></body></html>"
        return html

    @staticmethod
    def _score_bar(score: float) -> str:
        filled = int(score * 20)
        return "█" * filled + "░" * (20 - filled)


class ReportGenerator:
    """报告生成器 — 汇聚所有分析结果"""

    async def generate(
        self,
        doc: InternalDoc,
        format_issues: Optional[List[Dict]] = None,
        refs: Optional[List[ReferenceData]] = None,
        literature_papers: Optional[List[Dict]] = None,
        survey_result: Optional[Any] = None,
        submission_result: Optional[Any] = None,
        citation_analysis_text: str = "",
        missing_refs: Optional[List[str]] = None,
    ) -> AnalysisReport:
        report = AnalysisReport(title=doc.metadata.get("title", "论文分析报告"))
        report.doc_meta = doc.metadata
        report.doc_stats = doc.to_dict()

        # 格式
        report.format_issues = format_issues or []
        report.format_score = max(0, 1.0 - len(report.format_issues) * 0.02)

        # 文献
        if refs:
            report.total_refs = len(refs)
            report.doi_missing = [r.ref_id for r in refs if not r.doi]
            report.citation_consistency = max(0, 1.0 - len(report.doi_missing) * 0.05)

        # 检索
        if literature_papers:
            report.literature_found = len(literature_papers)
            report.literature_papers = literature_papers[:20]

        # 引文
        report.citation_analysis = citation_analysis_text
        report.missing_refs = missing_refs or []

        # 综述
        if survey_result:
            report.survey_sections = survey_result.get("sections", [])
            report.survey_trends = survey_result.get("trends", [])

        # 投稿
        if submission_result:
            report.submission_ready = submission_result.get("ready")
            report.submission_report = submission_result

        # 综合
        report.overall_score = round(
            report.format_score * 0.3 +
            report.citation_consistency * 0.3 +
            min(1.0, report.literature_found / 20) * 0.2 +
            0.2  # 基础分
        , 2)

        logger.info(f"报告生成完成: {report.title[:40]}... score={report.overall_score}")
        return report

    async def generate_and_save(
        self,
        output_path: str,
        fmt: str = "markdown",
        **kwargs,
    ) -> str:
        report = await self.generate(**kwargs)
        content = report.to_markdown() if fmt == "markdown" else report.to_html()
        Path(output_path).write_text(content, encoding="utf-8")
        logger.info(f"报告已保存: {output_path}")
        return output_path
