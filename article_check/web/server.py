"""
FastAPI Web 服务器 — Article Check 图形化界面后端

提供 REST API + SSE 流式批处理 + 文件上传，供 React 前端调用。

启动:
    python -m article_check.web.server
    或
    article-check web
"""
from __future__ import annotations
import asyncio
import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ─── Pydantic Models ───────────────────────────────────

class ReviewRequest(BaseModel):
    paper_path: str
    template: Optional[str] = None
    depth: str = "auto"
    with_deep_review: bool = False


class SearchRequest(BaseModel):
    query: str
    sources: List[str] = ["semantic_scholar", "openalex", "crossref", "arxiv"]
    limit_per_source: int = 10


class SurveyRequest(BaseModel):
    query: str
    depth: str = "standard"
    existing_refs: Optional[List[str]] = None


class SubmissionCheckRequest(BaseModel):
    paper_path: str
    journal: str
    stage: str = "initial"


class FixRequest(BaseModel):
    paper_path: str
    issues: List[Dict[str, Any]]


# ─── FastAPI App ────────────────────────────────────────

app = FastAPI(
    title="Article Check API",
    description="学术论文审查与文献调研系统",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)


# ─── Helper ─────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    # 确保关键目录存在
    for d in [UPLOAD_DIR, REPORT_DIR, Path(".worktrees")]:
        d.mkdir(exist_ok=True)


def api_success(data: Any = None, message: str = "ok") -> dict:
    return {"status": "ok", "data": data, "message": message}


def api_error(message: str, code: int = 400) -> dict:
    return {"status": "error", "message": message, "code": code}


# ─── System ─────────────────────────────────────────────

@app.get("/api/status")
async def get_status():
    """系统状态检查"""
    from article_check.config.settings import config
    from article_check.rules.registry import template_registry
    from article_check.references import ReferenceEngine
    from article_check.literature import LiteratureSearcher, SurveyGenerator

    return api_success({
        "version": "0.3.0",
        "deepseek_api": bool(config.deepseek.api_key),
        "templates": template_registry.count,
        "templates_list": [t.name for t in template_registry.list_all()],
        "lit_sources": ["semantic_scholar", "openalex", "crossref", "arxiv"],
    })


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传论文文件"""
    file_id = str(uuid.uuid4())[:8]
    suffix = Path(file.filename).suffix if file.filename else ".docx"
    save_path = UPLOAD_DIR / f"{file_id}{suffix}"
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)
    return api_success({
        "file_id": file_id,
        "filename": file.filename,
        "path": str(save_path),
        "size": len(content),
        "type": suffix.lstrip("."),
    })


# ─── Review ─────────────────────────────────────────────

@app.post("/api/review")
async def review_paper(req: ReviewRequest):
    """审查单篇论文（格式 + 内容 + 文献）"""
    from article_check.mcp.tools.format_tools import check_docx_format, check_latex_format, check_structure
    from article_check.utils.file_utils import detect_file_type

    path = Path(req.paper_path)
    if not path.exists():
        raise HTTPException(404, f"文件不存在: {req.paper_path}")

    ft = detect_file_type(path)
    issues = []
    if ft == "docx":
        issues = check_docx_format(str(path))
    elif ft == "latex":
        issues = check_latex_format(str(path))
    struct = check_structure(file_path=str(path), file_type=ft)

    # 文献提取
    from article_check.references import ReferenceEngine
    re = ReferenceEngine()
    refs = re.extract_from_paper(str(path))
    ref_result = re.validate(str(path), refs)

    return api_success({
        "file_type": ft,
        "format_issues": issues,
        "structure": struct,
        "references": {
            "count": len(refs),
            "matched": ref_result.matched,
            "total_refs": ref_result.total_refs,
            "score": ref_result.score,
            "doi_missing": len(ref_result.doi_missing),
        },
        "sections": struct.get("found_sections", []),
    })


@app.post("/api/review/deep")
async def deep_review(req: ReviewRequest):
    """深度审查（含 DeepSeek 内容分析）"""
    path = Path(req.paper_path)
    if not path.exists():
        raise HTTPException(404, "文件不存在")

    from article_check.pipeline.orchestrator import Orchestrator, PaperTask
    from article_check.pipeline.worker import FormatWorker, ContentWorker, ReferenceWorker
    from article_check.pipeline.reviewer import Reviewer
    from article_check.llm.client.deepseek import DeepSeekClient

    orch = Orchestrator()
    orch.register_worker(FormatWorker(orch.harness))
    if req.with_deep_review:
        orch.register_worker(ContentWorker(orch.harness, DeepSeekClient()))
    orch.register_worker(ReferenceWorker(orch.harness))
    orch.register_reviewer(Reviewer())

    task = PaperTask(
        task_id=path.stem,
        paper_path=path,
        title=path.stem,
        file_type="docx" if path.suffix == ".docx" else "latex",
        review_depth=req.depth,
    )
    result = await orch.review_single(task)

    return api_success({
        "task_id": result.task_id,
        "score": result.overall_score,
        "duration": result.duration,
        "report_path": str(result.report_path) if result.report_path else None,
        "errors": result.errors,
    })


# ─── Literature Search ──────────────────────────────────

@app.post("/api/literature/search")
async def search_literature(req: SearchRequest):
    """多源平行文献搜索"""
    from article_check.literature import LiteratureSearcher
    searcher = LiteratureSearcher()
    papers = await searcher.parallel_search(
        req.query,
        sources=req.sources,
        limit_per_source=req.limit_per_source,
    )
    return api_success({
        "query": req.query,
        "sources": req.sources,
        "count": len(papers),
        "papers": [
            {
                "title": p.title[:120],
                "authors": p.authors[:3],
                "year": p.year,
                "doi": p.doi,
                "venue": p.venue,
                "citation_count": p.citation_count,
                "source": p.source,
            }
            for p in papers
        ],
    })


# ─── Citation Network ───────────────────────────────────

@app.post("/api/literature/citation-network")
async def citation_network(papers: List[Dict[str, Any]]):
    """引文网络分析"""
    from article_check.literature.citation import CitationAnalyzer, CitationNode
    analyzer = CitationAnalyzer()
    nodes = [
        CitationNode(
            paper_id=p.get("id", f"p{i}"),
            title=p.get("title", ""),
            year=p.get("year"),
            citations_count=p.get("citations", 0),
            doi=p.get("doi"),
        )
        for i, p in enumerate(papers)
    ]
    for node in nodes:
        analyzer.graph.nodes[node.paper_id] = node
    return api_success({
        "nodes": [
            {"id": n.paper_id, "title": n.title[:50], "year": n.year, "citations": n.citations_count}
            for n in nodes
        ],
    })


# ─── Survey ─────────────────────────────────────────────

@app.post("/api/literature/survey")
async def generate_survey(req: SurveyRequest):
    """自动综述生成"""
    from article_check.literature import SurveyGenerator
    gen = SurveyGenerator()
    survey = await gen.generate(req.query, req.existing_refs, req.depth)
    return api_success({
        "title": survey.title,
        "abstract": survey.abstract,
        "sections": [
            {
                "title": s.title,
                "paper_count": len(s.papers),
                "papers": [
                    {"title": p.title[:60], "year": p.year, "authors": p.authors[:2]}
                    for p in s.papers[:8]
                ],
            }
            for s in survey.sections
        ],
        "trends": survey.trends,
        "missing_refs": [
            {"title": p.title[:60], "year": p.year}
            for p in survey.missing_refs
        ],
    })


@app.get("/api/literature/survey/markdown")
async def get_survey_markdown(query: str = Query(...)):
    """获取综述 Markdown"""
    from article_check.literature import SurveyGenerator
    gen = SurveyGenerator()
    survey = asyncio.run(gen.generate(query))
    return HTMLResponse(survey.to_markdown())


# ─── Submission Check ───────────────────────────────────

@app.post("/api/check/submission")
async def check_submission(req: SubmissionCheckRequest):
    """投稿就绪检查"""
    from article_check.checkers import SubmissionChecker
    checker = SubmissionChecker(req.journal, req.stage)
    report = checker.check(req.paper_path)
    return api_success({
        "journal": report.journal,
        "stage": report.stage,
        "passed": report.passed,
        "failed": report.failed,
        "total": report.total,
        "ready": report.ready,
        "items": [
            {
                "name": i.name,
                "category": i.category,
                "status": i.status,
                "detail": i.detail,
                "suggestion": i.suggestion,
            }
            for i in report.items
        ],
    })


# ─── Fix ────────────────────────────────────────────────

@app.post("/api/fix")
async def fix_paper(req: FixRequest):
    """自动修正论文格式"""
    from article_check.fixers import DocxAutoFixer
    fixer = DocxAutoFixer()
    fixes = fixer.apply(req.paper_path, req.issues)
    return api_success({
        "fixes": fixes,
        "count": len(fixes),
    })


# ─── Stream Review (SSE) ───────────────────────────────

@app.post("/api/review/batch-stream")
async def batch_review_stream(paths: List[str]):
    """流式批量审查 — SSE 推送"""
    from article_check.pipeline.streaming import StreamingOrchestrator
    from article_check.pipeline.models import PaperTask
    from article_check.utils.file_utils import detect_file_type

    async def event_stream():
        orch = StreamingOrchestrator()
        orch.register_worker(FormatWorker(orch.harness))
        orch.register_worker(ReferenceWorker(orch.harness))
        from article_check.llm.client.deepseek import DeepSeekClient
        from article_check.pipeline.worker import ContentWorker
        if config.deepseek.api_key:
            orch.register_worker(ContentWorker(orch.harness, DeepSeekClient()))
        orch.register_reviewer(Reviewer())

        tasks = [
            PaperTask(task_id=Path(p).stem, paper_path=Path(p), title=Path(p).stem, file_type=detect_file_type(Path(p)))
            for p in paths
        ]

        total = len(tasks)
        yield f"data: {json.dumps({'type': 'start', 'total': total})}\n\n"

        async for result in orch.review_batch_stream(tasks):
            data = {
                "type": "result",
                "paper_title": result.paper_title,
                "score": result.overall_score,
                "duration": result.duration,
                "errors": result.errors,
                "report_path": str(result.report_path) if result.report_path else None,
            }
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'complete'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ─── Static Files / SPA ────────────────────────────────

from fastapi.staticfiles import StaticFiles

FRONTEND_DIR = Path(__file__).parent / "frontend" / "dist"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


# ─── CLI Entry ──────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "article-check-api"}


def run_server(host: str = "127.0.0.1", port: int = 8765):
    """启动 Web 服务器"""
    import uvicorn
    print(f"🌐 Article Check Web UI: http://{host}:{port}")
    print(f"📚 API 文档: http://{host}:{port}/docs")
    print(f"🔍 按 Ctrl+C 停止")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
