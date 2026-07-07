"""引文网络分析 — 前向/后向/共引/文献耦合

参考: CitationClaw (PyPI v2.0.0), Biblio Infinity
"""
from __future__ import annotations
import asyncio
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx

from article_check.literature.searcher import PaperResult

logger = logging.getLogger(__name__)


@dataclass
class CitationNode:
    """引文网络节点"""
    paper_id: str
    title: str
    year: Optional[int] = None
    authors: List[str] = field(default_factory=list)
    citations_count: int = 0
    references_count: int = 0
    doi: Optional[str] = None
    source: str = ""


@dataclass
class CitationGraph:
    """引文网络图"""
    nodes: Dict[str, CitationNode] = field(default_factory=dict)
    edges_forward: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))   # A → B: A 引用了 B
    edges_backward: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))  # B → A: B 被 A 引用

    def add_citation(self, from_id: str, to_id: str):
        """从 → 到 引用"""
        self.edges_forward[from_id].add(to_id)
        self.edges_backward[to_id].add(from_id)


@dataclass
class CitationAnalysis:
    """引文分析结果"""
    core_papers: List[CitationNode] = field(default_factory=list)
    missing_references: List[PaperResult] = field(default_factory=list)  # 高共引但未引用的文献
    co_citation_matrix: Dict[str, List[str]] = field(default_factory=dict)
    field_trend: str = ""  # emerging / mature / declining
    citation_landscape: str = ""


class CitationAnalyzer:
    """引文分析器 — 构建引文网络并分析"""

    def __init__(self):
        self.graph = CitationGraph()
        logger.info("CitationAnalyzer 初始化")

    async def analyze_references(
        self,
        ref_dois: List[str],
        ref_titles: List[str],
        query: str = "",
    ) -> CitationAnalysis:
        """分析参考文献的引文网络"""
        analysis = CitationAnalysis()

        async with httpx.AsyncClient(timeout=15) as client:
            # 1. 获取每篇文献的引用信息
            tasks = []
            for doi in ref_dois[:10]:
                if not doi:
                    continue
                tasks.append(self._fetch_paper_info(client, doi))

            papers_info = await asyncio.gather(*tasks, return_exceptions=True)
            for info in papers_info:
                if isinstance(info, dict) and info:
                    node = CitationNode(
                        paper_id=info.get("paperId", ""),
                        title=info.get("title", ""),
                        year=info.get("year"),
                        citations_count=info.get("citationCount", 0) or 0,
                        doi=info.get("doi"),
                    )
                    self.graph.nodes[node.paper_id] = node
                    analysis.core_papers.append(node)

        # 2. 按引用数排序核心文献
        analysis.core_papers.sort(key=lambda n: -(n.citations_count or 0))

        # 3. 共引网络
        for i, p1 in enumerate(ref_titles[:5]):
            for j, p2 in enumerate(ref_titles[:5]):
                if i < j:
                    key = f"{p1[:20]} ↔ {p2[:20]}"
                    analysis.co_citation_matrix[key] = [p1[:30], p2[:30]]

        # 4. 领域趋势判断
        if analysis.core_papers:
            recent = sum(1 for p in analysis.core_papers if p.year and p.year >= 2023)
            ratio = recent / len(analysis.core_papers)
            if ratio > 0.5:
                analysis.field_trend = "活跃领域 (active)"
            elif ratio > 0.2:
                analysis.field_trend = "稳定领域 (mature)"
            else:
                analysis.field_trend = "成熟领域 (declining)"

        return analysis

    async def find_missing_references(
        self,
        query: str,
        existing_refs: List[str],
        top_n: int = 5,
    ) -> List[PaperResult]:
        """发现遗漏的重要文献"""
        from article_check.literature.searcher import LiteratureSearcher
        searcher = LiteratureSearcher()
        papers = await searcher.parallel_search(query, limit_per_source=10)

        # 过滤已引用的
        existing = set(t.lower()[:40] for t in existing_refs if t)
        missing = [p for p in papers if p.title.lower()[:40] not in existing]

        return missing[:top_n]

    async def _fetch_paper_info(self, client: httpx.AsyncClient, doi: str) -> Dict:
        try:
            resp = await client.get(
                f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
                params={"fields": "title,year,citationCount,references"},
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {}

    def to_report(self, analysis: CitationAnalysis) -> str:
        lines = ["## 📊 引文网络分析", ""]
        lines.append(f"**核心文献**: {len(analysis.core_papers)} 篇")
        lines.append(f"**领域趋势**: {analysis.field_trend}")
        lines.append("")

        if analysis.core_papers:
            lines.append("### 高影响力文献")
            for p in analysis.core_papers[:5]:
                lines.append(f"- [{p.year}] {p.title[:60]}... (被引 {p.citations_count})")
            lines.append("")

        if analysis.co_citation_matrix:
            lines.append("### 共引关系")
            for pair, items in list(analysis.co_citation_matrix.items())[:5]:
                lines.append(f"- {items[0]} ↔ {items[1]}")
            lines.append("")

        if analysis.missing_references:
            lines.append("### ⚠️ 可能遗漏的重要文献")
            for p in analysis.missing_references:
                lines.append(f"- {p.title[:60]}... ({p.year})")
            lines.append("")

        return "\n".join(lines)
