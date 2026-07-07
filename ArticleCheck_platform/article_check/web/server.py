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
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from article_check.runtime import (
    answer_report_question,
    build_review_payload,
    build_runtime,
    create_paper_task,
    execute_review_task,
)

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


class ReportDialogueRequest(BaseModel):
    report_payload: Dict[str, Any]
    question: str


class ReportFileRequest(BaseModel):
    path: str


class EvidenceSnippetRequest(BaseModel):
    report_payload: Dict[str, Any]
    evidence_id: str
    context_radius: int = 3


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


def _resolve_safe_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser().resolve()
    allowed_roots = [
        Path.cwd().resolve(),
        REPORT_DIR.resolve(),
        UPLOAD_DIR.resolve(),
    ]
    if not any(root == path or root in path.parents for root in allowed_roots):
        raise HTTPException(403, "不允许访问该文件")
    if not path.exists():
        raise HTTPException(404, f"文件不存在: {raw_path}")
    return path


def _find_evidence(report_payload: Dict[str, Any], evidence_id: str) -> Dict[str, Any]:
    for record in report_payload.get("evidence_records", []) or []:
        if record.get("evidence_id") == evidence_id:
            return record
    raise HTTPException(404, f"未找到 evidence: {evidence_id}")


def _snippet_from_lines(lines: List[str], center_line: int, radius: int) -> Dict[str, Any]:
    line_index = max(0, center_line - 1)
    start = max(0, line_index - radius)
    end = min(len(lines), line_index + radius + 1)
    excerpt = [
        {"line_number": idx + 1, "text": lines[idx].rstrip("\n")}
        for idx in range(start, end)
    ]
    return {
        "mode": "line",
        "start_line": start + 1,
        "end_line": end,
        "focus_line": line_index + 1,
        "excerpt": excerpt,
    }


def _snippet_from_section(lines: List[str], section_name: str, radius: int) -> Dict[str, Any]:
    section_lower = section_name.lower().strip()
    section_tokens = [section_lower.replace("_", " "), section_lower.replace("-", " ")]
    for idx, line in enumerate(lines):
        line_lower = line.lower().strip()
        if any(token and token in line_lower for token in section_tokens):
            snippet = _snippet_from_lines(lines, idx + 1, max(radius, 6))
            snippet["mode"] = "section"
            snippet["matched_section"] = section_name
            return snippet
        if line_lower.startswith("\\section") or line_lower.startswith("#"):
            normalized_line = (
                line_lower
                .replace("\\section{", "")
                .replace("\\subsection{", "")
                .replace("}", "")
                .replace("#", "")
                .strip()
            )
            if any(token and token in normalized_line for token in section_tokens):
                snippet = _snippet_from_lines(lines, idx + 1, max(radius, 6))
                snippet["mode"] = "section"
                snippet["matched_section"] = section_name
                return snippet
    return {
        "mode": "section",
        "start_line": None,
        "end_line": None,
        "focus_line": None,
        "matched_section": section_name,
        "excerpt": [{"line_number": None, "text": f"未在源文件中定位到章节: {section_name}"}],
    }


def _build_snippet_summary(location: Dict[str, Any]) -> str:
    parts: List[str] = []
    if location.get("page"):
        parts.append(f"第 {location['page']} 页")
    if location.get("line"):
        parts.append(f"行 {location['line']}")
    if location.get("column"):
        parts.append(f"列 {location['column']}")
    if location.get("section"):
        parts.append(f"章节 {location['section']}")
    return " · ".join(parts) or "未提供定位信息"


def _read_text_excerpt(source_path: Path, location: Dict[str, Any], radius: int) -> Dict[str, Any]:
    suffix = source_path.suffix.lower()

    if suffix in {".tex", ".ltx", ".txt", ".md"}:
        lines = source_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if location.get("line"):
            snippet = _snippet_from_lines(lines, int(location["line"]), radius)
        elif location.get("section"):
            snippet = _snippet_from_section(lines, str(location["section"]), radius)
        else:
            snippet = _snippet_from_lines(lines, 1, max(radius, 8))
        snippet["source_kind"] = "text"
        snippet["summary"] = _build_snippet_summary(location)
        return snippet

    if suffix == ".docx":
        try:
            from docx import Document
        except Exception as exc:  # pragma: no cover - import fallback
            return {
                "mode": "docx-unavailable",
                "source_kind": "docx",
                "summary": _build_snippet_summary(location),
                "excerpt": [{"line_number": None, "text": f"DOCX 片段预览不可用: {exc}"}],
            }

        doc = Document(str(source_path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        lines = [text.strip() for text in paragraphs]
        if location.get("section"):
            snippet = _snippet_from_section(lines, str(location["section"]), max(radius, 4))
        elif location.get("line"):
            snippet = _snippet_from_lines(lines, int(location["line"]), radius)
        else:
            snippet = _snippet_from_lines(lines, 1, max(radius, 5))
        snippet["source_kind"] = "docx"
        snippet["summary"] = _build_snippet_summary(location)
        return snippet

    if suffix == ".pdf":
        try:
            import fitz
        except Exception as exc:  # pragma: no cover - import fallback
            return {
                "mode": "pdf-unavailable",
                "source_kind": "pdf",
                "summary": _build_snippet_summary(location),
                "excerpt": [{"line_number": None, "text": f"PDF 片段预览不可用: {exc}"}],
            }

        page_number = max(1, int(location.get("page") or 1))
        with fitz.open(str(source_path)) as pdf:
            page = pdf.load_page(page_number - 1)
            text = page.get_text("text")
        lines = text.splitlines()
        snippet = _snippet_from_lines(lines, int(location.get("line") or 1), max(radius, 5))
        snippet["source_kind"] = "pdf"
        snippet["page"] = page_number
        snippet["summary"] = _build_snippet_summary(location)
        return snippet

    return {
        "mode": "unsupported",
        "source_kind": suffix.lstrip(".") or "unknown",
        "summary": _build_snippet_summary(location),
        "excerpt": [{"line_number": None, "text": f"暂不支持该文件类型的原文片段预览: {suffix or 'unknown'}"}],
    }


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
        "ai_provider": config.ai.provider,
        "dify_enabled": bool(config.dify.api_key),
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
    """审查单篇论文（统一 runtime 输出）"""
    path = Path(req.paper_path)
    if not path.exists():
        raise HTTPException(404, f"文件不存在: {req.paper_path}")

    runtime = build_runtime(
        mode="web",
        enable_deep_review=False,
        paper_paths=[str(path)],
        template_name=req.template,
    )
    task = create_paper_task(path, depth=req.depth, template_name=req.template)
    result = await execute_review_task(runtime, task, enable_deep_review=False)

    payload = build_review_payload(result, plan_id=runtime.plan.plan_id)
    payload["sections"]["structure"] = (
        result.format_check.get("structure", {}) if isinstance(result.format_check, dict) else {}
    )
    return api_success(payload)


@app.post("/api/review/deep")
async def deep_review(req: ReviewRequest):
    """深度审查（含 DeepSeek 内容分析）"""
    path = Path(req.paper_path)
    if not path.exists():
        raise HTTPException(404, "文件不存在")

    runtime = build_runtime(
        mode="web",
        enable_deep_review=req.with_deep_review,
        paper_paths=[str(path)],
        template_name=req.template,
    )
    task = create_paper_task(path, depth=req.depth, template_name=req.template)
    result = await execute_review_task(runtime, task, enable_deep_review=req.with_deep_review)
    return api_success(build_review_payload(result, plan_id=runtime.plan.plan_id))


@app.post("/api/report/dialogue")
async def report_dialogue(req: ReportDialogueRequest):
    """围绕结构化报告进行问答。"""
    answer = answer_report_question(req.report_payload, req.question)
    return api_success({"answer": answer})


@app.get("/api/report/file")
async def get_report_file(path: str = Query(..., description="报告文件路径")):
    """安全返回报告导出文件。"""
    file_path = _resolve_safe_path(path)
    if file_path.suffix.lower() == ".html":
        return HTMLResponse(file_path.read_text(encoding="utf-8"))
    if file_path.suffix.lower() == ".json":
        return PlainTextResponse(file_path.read_text(encoding="utf-8"), media_type="application/json")
    if file_path.suffix.lower() == ".md":
        return PlainTextResponse(file_path.read_text(encoding="utf-8"), media_type="text/markdown; charset=utf-8")
    return FileResponse(str(file_path))


@app.post("/api/report/source-snippet")
async def get_report_source_snippet(req: EvidenceSnippetRequest):
    """根据 evidence 定位并返回原文片段。"""
    report_payload = req.report_payload or {}
    evidence = _find_evidence(report_payload, req.evidence_id)
    source_path_raw = (
        (report_payload.get("meta") or {}).get("source_paper_path")
        or (report_payload.get("formal_report") or {}).get("source_paper_path")
    )
    if not source_path_raw:
        raise HTTPException(400, "报告中缺少 source_paper_path，无法定位原文片段")

    source_path = _resolve_safe_path(source_path_raw)
    snippet = _read_text_excerpt(source_path, evidence.get("location") or {}, req.context_radius)
    return api_success({
        "evidence_id": req.evidence_id,
        "source_path": str(source_path),
        "source_name": source_path.name,
        "location": evidence.get("location") or {},
        "claim": evidence.get("claim") or "",
        "snippet": snippet,
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
    survey = await gen.generate(query)
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
    async def event_stream():
        runtime = build_runtime(
            mode="batch",
            enable_deep_review=True,
            enable_streaming=True,
            paper_paths=paths,
        )
        tasks = [create_paper_task(p) for p in paths]

        total = len(tasks)
        yield f"data: {json.dumps({'type': 'start', 'total': total})}\n\n"

        async for result in runtime.orchestrator.review_batch_stream(tasks):
            data = {
                "type": "result",
                "paper_title": result.paper_title,
                "score": result.overall_score,
                "duration": result.duration,
                "errors": result.errors,
                "report_path": str(result.report_path) if result.report_path else None,
                "review_payload": build_review_payload(result, plan_id=runtime.plan.plan_id),
            }
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'complete'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ─── Static Files / SPA ────────────────────────────────

from fastapi.staticfiles import StaticFiles

FRONTEND_DIR = Path(__file__).parent / "frontend" / "dist"
ASSETS_DIR = FRONTEND_DIR / "assets"
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="frontend-assets")


@app.get("/", response_class=HTMLResponse)
async def frontend_index():
    if not FRONTEND_DIR.exists():
        raise HTTPException(404, "前端构建文件不存在")
    return HTMLResponse((FRONTEND_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/{full_path:path}")
async def frontend_spa_fallback(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(404, "API 路径不存在")
    if not FRONTEND_DIR.exists():
        raise HTTPException(404, "前端构建文件不存在")

    requested = (FRONTEND_DIR / full_path).resolve()
    if requested.exists() and requested.is_file() and FRONTEND_DIR.resolve() in requested.parents:
        return FileResponse(str(requested))

    index_path = FRONTEND_DIR / "index.html"
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


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
