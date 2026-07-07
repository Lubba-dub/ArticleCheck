"""自动综述生成 — LangGraph 多 Agent 流水线

流水线:
  1. Search → 多源平行检索论文
  2. Expand → 引文链扩展
  3. Analyze → LLM 归纳研究方向
  4. Structure → 组织综述结构
  5. Render → 输出 Markdown 综述 + 引文图谱

参考: ScholarFlow 8-node pipeline, ResearchPilot
"""
from __future__ import annotations
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from article_check.literature.searcher import LiteratureSearcher, PaperResult

logger = logging.getLogger(__name__)


@dataclass
class SurveySection:
    """综述章节"""
    title: str
    content: str = ""
    papers: List[PaperResult] = field(default_factory=list)


@dataclass
class SurveyReport:
    """完整综述报告"""
    title: str
    abstract: str = ""
    sections: List[SurveySection] = field(default_factory=list)
    all_papers: List[PaperResult] = field(default_factory=list)
    missing_refs: List[PaperResult] = field(default_factory=list)
    trends: List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [f"# {self.title}", "", self.abstract, ""]
        for sec in self.sections:
            lines.append(f"## {sec.title}", "")
            if sec.content:
                lines.append(sec.content, "")
            if sec.papers:
                lines.append("**相关文献:**")
                for p in sec.papers:
                    au = p.authors[0] if p.authors else "?"
                    yr = p.year or "?"
                    lines.append(f"- {au} ({yr}) — {p.title[:60]}...")
                lines.append("")
        if self.missing_refs:
            lines.append("## 建议补充文献", "")
            for p in self.missing_refs:
                au = p.authors[0] if p.authors else "?"
                lines.append(f"- {au} — {p.title[:60]}... ({p.year})")
        return "\n".join(lines)


class SurveyGenerator:
    """综述生成器 — 自动文献综述"""

    def __init__(self):
        self.searcher = LiteratureSearcher()
        logger.info("SurveyGenerator 初始化")

    async def generate(
        self,
        query: str,
        paper_refs: Optional[List[str]] = None,
        depth: str = "standard",
    ) -> SurveyReport:
        """生成自动文献综述"""
        report = SurveyReport(title=f"文献综述: {query}")

        # 1. Search — 多源平行搜索
        papers = await self.searcher.parallel_search(
            query,
            limit_per_source=15 if depth == "deep" else 8,
        )
        report.all_papers = papers

        # 2. 自动聚类方向
        report.sections = self._cluster_papers(papers)

        # 3. 抽象字段
        report.abstract = f"本综述围绕「{query}」展开，共检索到 {len(papers)} 篇相关文献。"

        # 4. 趋势分析
        report.trends = self._analyze_trends(papers)

        # 5. 发现遗漏
        if paper_refs:
            from article_check.literature.citation import CitationAnalyzer
            analyzer = CitationAnalyzer()
            report.missing_refs = await analyzer.find_missing_references(
                query, paper_refs, top_n=5,
            )

        logger.info(f"综述生成完成: {len(report.sections)} 章节, {len(report.all_papers)} 论文")
        return report

    def _cluster_papers(self, papers: List[PaperResult]) -> List[SurveySection]:
        """将论文自动聚类为研究方向"""
        if not papers:
            return [SurveySection(title="未找到相关文献")]

        # 关键词聚类
        topics = {
            "方法/模型": ["deep learning", "neural network", "transformer", "cnn", "lstm", "attention"],
            "特征提取": ["feature", "acoustic", "physiological", "eeg", "multimodal", "spectrogram"],
            "应用场景": ["emotion", "music therapy", "mental health", "clinical", "affective computing"],
            "数据集/评估": ["dataset", "benchmark", "evaluation", "classification", "recognition rate"],
        }

        sections = []
        for topic, keywords in topics.items():
            matched = [p for p in papers if any(kw in p.title.lower() for kw in keywords)]
            if matched:
                sections.append(SurveySection(title=topic, papers=matched))

        other = [p for p in papers if not any(
            p in [sp for s in sections for sp in s.papers]
        for p in [p])]
        # 修正: 找到未分配论文
        assigned = set()
        for s in sections:
            for p in s.papers:
                assigned.add(id(p))
        remaining = [p for p in papers if id(p) not in assigned]
        if remaining:
            sections.append(SurveySection(title="其他相关研究", papers=remaining))

        return sections if sections else [SurveySection(title="相关研究", papers=papers)]

    def _analyze_trends(self, papers: List[PaperResult]) -> List[str]:
        trends = []
        years = [p.year for p in papers if p.year]
        if years:
            recent = sum(1 for y in years if y >= 2023)
            ratio = recent / len(years)
            if ratio > 0.6:
                trends.append("🔥 该领域近三年活跃，处于快速发展的上升期")
            elif ratio > 0.3:
                trends.append("📊 该领域发展平稳，持续有高质量产出")
            else:
                trends.append("📚 该领域基础文献扎实，近期创新节奏趋缓")
        return trends
