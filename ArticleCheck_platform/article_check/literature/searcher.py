"""多源文献平行检索 — 5 个学术数据源并发搜索

当前接入:
  - Semantic Scholar (graph/v1, 100 req/s)
  - OpenAlex (REST, 100k req/day)
  - CrossRef (REST, 50 req/s)
  - arXiv (API, 无限制) ✅ 已接

参考: ScholarFlow (8-node LangGraph pipeline)
"""
from __future__ import annotations
import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlencode

import httpx

logger = logging.getLogger(__name__)

MAX_CONCURRENT = 8  # 并发请求上限


@dataclass
class PaperResult:
    """检索结果中的一篇论文"""
    title: str = ""
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    abstract: str = ""
    doi: Optional[str] = None
    url: Optional[str] = None
    venue: Optional[str] = None
    citation_count: Optional[int] = None
    source: str = ""   # semantic_scholar / openalex / crossref / arxiv
    relevance_score: float = 0.0


@dataclass
class SearchResult:
    """一次检索的结果"""
    query: str
    papers: List[PaperResult] = field(default_factory=list)
    total_found: int = 0
    source: str = ""
    error: Optional[str] = None
    duration: float = 0.0


class SemanticScholarSearcher:
    """Semantic Scholar API 检索"""

    BASE = "https://api.semanticscholar.org/graph/v1"

    async def search(self, query: str, limit: int = 20) -> SearchResult:
        import time
        start = time.time()
        result = SearchResult(query=query, source="semantic_scholar")
        try:
            params = {
                "query": query,
                "limit": min(limit, 100),
                "fields": "title,authors,year,externalIds,abstract,venue,citationCount",
            }
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"{self.BASE}/paper/search", params=params)
                resp.raise_for_status()
                data = resp.json()
            result.total_found = data.get("total", 0)
            for p in data.get("data", []):
                paper = PaperResult(
                    title=p.get("title", ""),
                    authors=[a.get("name", "") for a in p.get("authors", []) if a.get("name")],
                    year=p.get("year"),
                    abstract=(p.get("abstract") or "")[:500],
                    doi=p.get("externalIds", {}).get("DOI"),
                    url=f"https://api.semanticscholar.org/CorpusID:{p.get('paperId', '')}" if p.get("paperId") else None,
                    venue=p.get("venue"),
                    citation_count=p.get("citationCount"),
                    source="semantic_scholar",
                )
                result.papers.append(paper)
        except Exception as e:
            result.error = str(e)
            logger.warning(f"Semantic Scholar 检索失败: {e}")
        result.duration = time.time() - start
        return result


class OpenAlexSearcher:
    """OpenAlex API 检索"""

    BASE = "https://api.openalex.org"

    async def search(self, query: str, limit: int = 20) -> SearchResult:
        import time
        start = time.time()
        result = SearchResult(query=query, source="openalex")
        try:
            params = {
                "search": query,
                "per_page": min(limit, 200),
                "sort": "relevance_score:desc",
            }
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"{self.BASE}/works", params=params)
                resp.raise_for_status()
                data = resp.json()
            result.total_found = data.get("meta", {}).get("count", 0)
            for w in data.get("results", []):
                paper = PaperResult(
                    title=w.get("title", ""),
                    authors=[a.get("author", {}).get("display_name", "") for a in w.get("authorships", []) if a.get("author")],
                    year=w.get("publication_year"),
                    abstract=w.get("abstract_inverted_index", ""),
                    doi=w.get("doi", "").replace("https://doi.org/", "") if w.get("doi") else None,
                    url=w.get("open_access", {}).get("oa_url") if w.get("open_access") else None,
                    venue=w.get("primary_location", {}).get("source", {}).get("display_name") if w.get("primary_location") else None,
                    citation_count=w.get("cited_by_count"),
                    source="openalex",
                )
                result.papers.append(paper)
        except Exception as e:
            result.error = str(e)
            logger.warning(f"OpenAlex 检索失败: {e}")
        result.duration = time.time() - start
        return result


class CrossrefSearcher:
    """CrossRef API 检索"""

    BASE = "https://api.crossref.org/works"

    async def search(self, query: str, limit: int = 20) -> SearchResult:
        import time
        start = time.time()
        result = SearchResult(query=query, source="crossref")
        try:
            params = {"query": query, "rows": min(limit, 50)}
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(self.BASE, params=params)
                resp.raise_for_status()
                data = resp.json()
            items = data.get("message", {}).get("items", [])
            result.total_found = data.get("message", {}).get("total-results", 0)
            for w in items:
                paper = PaperResult(
                    title=w.get("title", [""])[0] if w.get("title") else "",
                    authors=[a.get("given", "") + " " + a.get("family", "") for a in w.get("author", [])],
                    year=(w.get("published-print", {}).get("date-parts", [[None]])[0][0]
                          or w.get("created", {}).get("date-parts", [[None]])[0][0]),
                    doi=w.get("DOI"),
                    url=w.get("URL"),
                    venue=w.get("container-title", [""])[0] if w.get("container-title") else None,
                    source="crossref",
                )
                result.papers.append(paper)
        except Exception as e:
            result.error = str(e)
            logger.warning(f"CrossRef 检索失败: {e}")
        result.duration = time.time() - start
        return result


class ArxivSearcher:
    """arXiv API 检索"""

    BASE = "http://export.arxiv.org/api/query"

    async def search(self, query: str, limit: int = 20) -> SearchResult:
        import time
        start = time.time()
        result = SearchResult(query=query, source="arxiv")
        try:
            params = urlencode({
                "search_query": f"all:{query}",
                "start": 0, "max_results": min(limit, 50),
                "sortBy": "relevance", "sortOrder": "descending",
            })
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(f"{self.BASE}?{params}")
                resp.raise_for_status()
            root = ET.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall("atom:entry", ns)
            result.total_found = len(entries)
            for entry in entries:
                title_el = entry.find("atom:title", ns)
                summary_el = entry.find("atom:summary", ns)
                id_el = entry.find("atom:id", ns)
                published_el = entry.find("atom:published", ns)
                authors = []
                for a in entry.findall("atom:author", ns):
                    name = a.find("atom:name", ns)
                    if name is not None:
                        authors.append(name.text)
                paper = PaperResult(
                    title=(title_el.text or "").strip().replace("\n", " ") if title_el is not None else "",
                    authors=authors,
                    year=int((published_el.text or "")[:4]) if published_el is not None and published_el.text else None,
                    abstract=(summary_el.text or "").strip().replace("\n", " ")[:500] if summary_el is not None else "",
                    url=id_el.text.strip() if id_el is not None and id_el.text else None,
                    source="arxiv",
                )
                result.papers.append(paper)
        except Exception as e:
            result.error = str(e)
            logger.warning(f"arXiv 检索失败: {e}")
        result.duration = time.time() - start
        return result


class LiteratureSearcher:
    """
    文献检索器 — 多源平行搜索 + 去重 + 排序

    用法:
        searcher = LiteratureSearcher()
        results = await searcher.parallel_search(
            "music emotion recognition",
            sources=["semantic_scholar", "openalex", "crossref", "arxiv"],
        )
    """

    def __init__(self):
        self._sources = {
            "semantic_scholar": SemanticScholarSearcher(),
            "openalex": OpenAlexSearcher(),
            "crossref": CrossrefSearcher(),
            "arxiv": ArxivSearcher(),
        }
        logger.info(f"LiteratureSearcher: {len(self._sources)} 个数据源就绪")

    async def parallel_search(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        limit_per_source: int = 20,
        timeout: float = 30.0,
    ) -> List[PaperResult]:
        """多源并发检索 → 去重 → 排序"""
        if sources is None:
            sources = list(self._sources.keys())

        sem = asyncio.Semaphore(MAX_CONCURRENT)

        async def search_one(src: str) -> SearchResult:
            async with sem:
                searcher = self._sources.get(src)
                if not searcher:
                    return SearchResult(query=query, source=src, error="未知数据源")
                return await searcher.search(query, limit_per_source)

        raw = await asyncio.gather(
            *[search_one(s) for s in sources],
            return_exceptions=True,
        )

        all_papers = []
        for r in raw:
            if isinstance(r, SearchResult):
                all_papers.extend(r.papers)
                logger.info(f"  {r.source}: {len(r.papers)} papers in {r.duration:.1f}s")
            elif isinstance(r, Exception):
                logger.warning(f"  检索异常: {r}")

        # 去重 (按 DOI / 标题相似度)
        seen_dois = set()
        seen_titles = set()
        deduped = []
        for p in all_papers:
            if p.doi and p.doi in seen_dois:
                continue
            if p.doi:
                seen_dois.add(p.doi)
            title_key = p.title.lower().strip()[:50] if p.title else ""
            if title_key and title_key in seen_titles:
                continue
            if title_key:
                seen_titles.add(title_key)
            deduped.append(p)

        # 排序: 有引用数按引用数, 否则按来源优先级
        source_priority = {"semantic_scholar": 0, "openalex": 1, "crossref": 2, "arxiv": 3}
        deduped.sort(key=lambda p: (
            -(p.citation_count or 0),
            source_priority.get(p.source, 99),
        ))

        logger.info(f"平行检索完成: {len(all_papers)} → 去重后 {len(deduped)} 篇")
        return deduped

    async def fetch_citations(self, doi: str) -> Dict[str, Any]:
        """获取单篇论文的引用信息"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
                    "?fields=title,citationCount,references(referenceCount)",
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning(f"引用获取失败: {e}")
        return {}
