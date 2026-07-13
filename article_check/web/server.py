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
import re
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
from article_check.dify_review import (
    dify_workflows_available,
    get_dify_registry_status,
    run_dify_report_qa,
    run_dify_review_chain,
)

logger = logging.getLogger(__name__)

# ─── Pydantic Models ───────────────────────────────────

class ReviewRequest(BaseModel):
    paper_path: str
    template: Optional[str] = None
    depth: str = "auto"
    with_deep_review: bool = False
    review_track: str = "auto"
    institution: Optional[str] = None
    review_focus: Optional[str] = None
    report_focus: Optional[str] = None


class BatchReviewRequest(BaseModel):
    paths: List[str]
    with_deep_review: bool = True
    review_track: str = "auto"
    template: Optional[str] = None


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
    matched_index = _find_section_line_index(lines, section_name)
    if matched_index is not None:
        snippet = _snippet_from_lines(lines, matched_index + 1, max(radius, 6))
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


def _normalize_search_text(text: Any) -> str:
    value = str(text or "").strip().lower()
    value = value.replace("_", " ").replace("-", " ")
    value = re.sub(r"[^\w\u4e00-\u9fff\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _is_useful_query(text: str) -> bool:
    normalized = _normalize_search_text(text)
    if not normalized:
        return False
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", normalized)
    if len(chinese_chars) >= 2:
        return True
    compact = normalized.replace(" ", "")
    return len(compact) >= 6


def _split_search_candidates(text: Any) -> List[str]:
    raw = str(text or "").strip()
    if not raw:
        return []
    segments = [raw]
    segments.extend(re.split(r"[，。；;：:,.!?()\[\]{}]+", raw))
    values: List[str] = []
    seen = set()
    for item in segments:
        normalized = _normalize_search_text(item)
        if not normalized or normalized in seen or not _is_useful_query(normalized):
            continue
        seen.add(normalized)
        values.append(normalized)
    return values


def _expand_section_tokens(section_name: Any) -> List[str]:
    normalized = _normalize_search_text(section_name)
    if not normalized:
        return []

    variants = {
        normalized,
        normalized.replace(" ", ""),
        normalized.replace(" ", "_"),
        normalized.replace(" ", "-"),
    }

    alias_map = {
        "references": {"reference", "references", "bibliography", "参考文献", "参考资料", "文献"},
        "reference": {"reference", "references", "bibliography", "参考文献", "参考资料", "文献"},
        "bibliography": {"reference", "references", "bibliography", "参考文献", "参考资料", "文献"},
        "abstract": {"abstract", "摘要", "摘 要"},
        "introduction": {"introduction", "引言", "绪论", "前言"},
        "related work": {"related work", "relatedwork", "相关工作", "研究现状"},
        "conclusion": {"conclusion", "结论", "总结", "结语"},
        "method": {"method", "methods", "方法", "研究方法"},
    }
    for key, aliases in alias_map.items():
        if key in normalized:
            variants.update(_normalize_search_text(alias) for alias in aliases)

    return [token for token in variants if token]


def _build_search_queries(evidence: Dict[str, Any], location: Dict[str, Any]) -> List[str]:
    raw_payload = evidence.get("raw_payload") or {}
    candidates: List[Any] = [
        evidence.get("claim"),
        evidence.get("suggestion"),
        raw_payload.get("description"),
        raw_payload.get("issue"),
        raw_payload.get("title"),
        raw_payload.get("section"),
        location.get("section"),
    ]
    queries: List[str] = []
    seen = set()
    for candidate in candidates:
        for item in _split_search_candidates(candidate):
            if item in seen:
                continue
            seen.add(item)
            queries.append(item)
    return queries


def _is_heading_like_line(line: str) -> bool:
    stripped = str(line or "").strip()
    if not stripped:
        return False
    if len(stripped) <= 40:
        return True
    return bool(
        stripped.startswith("\\section")
        or stripped.startswith("\\subsection")
        or stripped.startswith("#")
        or re.match(r"^\s*[\d一二三四五六七八九十]+[\.、]", stripped)
    )


def _find_section_line_index(lines: List[str], section_name: Any) -> Optional[int]:
    section_tokens = _expand_section_tokens(section_name)
    if not section_tokens:
        return None

    for idx, line in enumerate(lines):
        if not _is_heading_like_line(line):
            continue
        normalized_line = _normalize_search_text(line)
        normalized_line = (
            normalized_line
            .replace("section ", "")
            .replace("subsection ", "")
            .strip()
        )
        if any(token and token in normalized_line for token in section_tokens):
            return idx
    return None


def _derive_section_name(evidence: Dict[str, Any], location: Dict[str, Any]) -> Optional[str]:
    if location.get("section"):
        return str(location["section"])

    raw_payload = evidence.get("raw_payload") or {}
    if raw_payload.get("section"):
        return str(raw_payload["section"])

    for text in [evidence.get("claim"), raw_payload.get("description"), raw_payload.get("title")]:
        raw = str(text or "")
        match = re.search(r"[\"'`]?([A-Za-z][A-Za-z\s_-]{1,40}|[\u4e00-\u9fff]{2,20})[\"'`]?\s*章节", raw)
        if match:
            return match.group(1).strip()
    return None


def _score_line_match(line: str, query: str) -> int:
    normalized_line = _normalize_search_text(line)
    if not normalized_line or not query:
        return 0
    if query in normalized_line:
        return 1000 + len(query)

    query_tokens = [token for token in query.split() if len(token) >= 2]
    if len(query_tokens) < 2:
        return 0

    matched = sum(1 for token in set(query_tokens) if token in normalized_line)
    required = max(2, len(query_tokens) // 2)
    if matched >= required:
        return matched * 100 + len(query)
    return 0


def _find_best_query_line(lines: List[str], queries: List[str]) -> Optional[Dict[str, Any]]:
    best_match: Optional[Dict[str, Any]] = None
    for idx, line in enumerate(lines):
        for query in queries:
            score = _score_line_match(line, query)
            if score <= 0:
                continue
            if not best_match or score > best_match["score"]:
                best_match = {
                    "line_index": idx,
                    "score": score,
                    "query": query,
                }
    return best_match


def _snippet_from_query(lines: List[str], queries: List[str], radius: int) -> Optional[Dict[str, Any]]:
    best_match = _find_best_query_line(lines, queries)
    if not best_match:
        return None

    snippet = _snippet_from_lines(lines, best_match["line_index"] + 1, max(radius, 4))
    snippet["mode"] = "query"
    snippet["matched_query"] = best_match["query"]
    return snippet


def _unresolved_snippet(source_kind: str, location: Dict[str, Any], message: str) -> Dict[str, Any]:
    return {
        "mode": "unresolved",
        "source_kind": source_kind,
        "summary": _build_snippet_summary(location),
        "excerpt": [{"line_number": None, "text": message}],
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


def _read_pdf_excerpt(source_path: Path, location: Dict[str, Any], evidence: Dict[str, Any], radius: int) -> Dict[str, Any]:
    try:
        import fitz
    except Exception as exc:  # pragma: no cover - import fallback
        return {
            "mode": "pdf-unavailable",
            "source_kind": "pdf",
            "summary": _build_snippet_summary(location),
            "excerpt": [{"line_number": None, "text": f"PDF 片段预览不可用: {exc}"}],
        }

    queries = _build_search_queries(evidence, location)
    preferred_page = int(location.get("page") or 0) or None
    section_name = _derive_section_name(evidence, location)

    with fitz.open(str(source_path)) as pdf:
        if preferred_page and location.get("line") and 1 <= preferred_page <= len(pdf):
            page = pdf.load_page(preferred_page - 1)
            lines = page.get_text("text").splitlines()
            snippet = _snippet_from_lines(lines, int(location.get("line") or 1), max(radius, 5))
            snippet["source_kind"] = "pdf"
            snippet["page"] = preferred_page
            snippet["summary"] = _build_snippet_summary(location)
            return snippet

        page_order = list(range(1, len(pdf) + 1))
        if preferred_page and preferred_page in page_order:
            page_order.remove(preferred_page)
            page_order.insert(0, preferred_page)

        if queries:
            best_match: Optional[Dict[str, Any]] = None
            for page_number in page_order:
                page = pdf.load_page(page_number - 1)
                lines = page.get_text("text").splitlines()
                candidate = _find_best_query_line(lines, queries)
                if candidate and (not best_match or candidate["score"] > best_match["score"]):
                    best_match = {
                        "page_number": page_number,
                        "line_index": candidate["line_index"],
                        "query": candidate["query"],
                        "lines": lines,
                        "score": candidate["score"],
                    }
            if best_match:
                snippet = _snippet_from_lines(best_match["lines"], best_match["line_index"] + 1, max(radius, 5))
                snippet["mode"] = "query"
                snippet["matched_query"] = best_match["query"]
                snippet["source_kind"] = "pdf"
                snippet["page"] = best_match["page_number"]
                snippet["summary"] = _build_snippet_summary(location)
                return snippet

        if section_name:
            for page_number in page_order:
                page = pdf.load_page(page_number - 1)
                lines = page.get_text("text").splitlines()
                matched_index = _find_section_line_index(lines, section_name)
                if matched_index is not None:
                    snippet = _snippet_from_lines(lines, matched_index + 1, max(radius, 6))
                    snippet["mode"] = "section"
                    snippet["matched_section"] = section_name
                    snippet["source_kind"] = "pdf"
                    snippet["page"] = page_number
                    snippet["summary"] = _build_snippet_summary(location)
                    return snippet

        if preferred_page and 1 <= preferred_page <= len(pdf):
            page = pdf.load_page(preferred_page - 1)
            lines = page.get_text("text").splitlines()
            snippet = _snippet_from_lines(lines, int(location.get("line") or 1), max(radius, 5))
            snippet["source_kind"] = "pdf"
            snippet["page"] = preferred_page
            snippet["summary"] = _build_snippet_summary(location)
            return snippet

        return _unresolved_snippet("pdf", location, "当前问题缺少稳定的页码、行号或文本锚点，暂时无法精确定位到对应 PDF 片段。")


def _read_text_excerpt(source_path: Path, location: Dict[str, Any], evidence: Dict[str, Any], radius: int) -> Dict[str, Any]:
    suffix = source_path.suffix.lower()

    if suffix in {".tex", ".ltx", ".txt", ".md"}:
        lines = source_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        section_name = _derive_section_name(evidence, location)
        if location.get("line"):
            snippet = _snippet_from_lines(lines, int(location["line"]), radius)
        elif (queries := _build_search_queries(evidence, location)) and (matched := _snippet_from_query(lines, queries, radius)):
            snippet = matched
        elif section_name:
            snippet = _snippet_from_section(lines, section_name, radius)
        else:
            return _unresolved_snippet("text", location, "当前问题缺少稳定的行号、章节或文本锚点，暂时无法精确定位到对应原文片段。")
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
        section_name = _derive_section_name(evidence, location)
        if location.get("line"):
            snippet = _snippet_from_lines(lines, int(location["line"]), radius)
        elif (queries := _build_search_queries(evidence, location)) and (matched := _snippet_from_query(lines, queries, radius)):
            snippet = matched
        elif section_name:
            snippet = _snippet_from_section(lines, section_name, max(radius, 4))
        else:
            return _unresolved_snippet("docx", location, "当前问题缺少稳定的段落、章节或文本锚点，暂时无法精确定位到对应 DOCX 片段。")
        snippet["source_kind"] = "docx"
        snippet["summary"] = _build_snippet_summary(location)
        return snippet

    if suffix == ".pdf":
        return _read_pdf_excerpt(source_path, location, evidence, radius)

    return {
        "mode": "unsupported",
        "source_kind": suffix.lstrip(".") or "unknown",
        "summary": _build_snippet_summary(location),
        "excerpt": [{"line_number": None, "text": f"暂不支持该文件类型的原文片段预览: {suffix or 'unknown'}"}],
    }


def _annotate_review_payload(
    payload: Dict[str, Any],
    *,
    backend: str,
    warning: Optional[str] = None,
) -> Dict[str, Any]:
    meta = payload.setdefault("meta", {})
    meta["review_backend"] = backend
    if warning:
        warnings = meta.setdefault("warnings", [])
        if warning not in warnings:
            warnings.append(warning)
        errors = payload.setdefault("errors", [])
        if warning not in errors:
            errors.append(warning)
    return payload


async def _run_local_review_payload(
    path: Path,
    req: ReviewRequest,
    *,
    enable_deep_review: bool,
    warning: Optional[str] = None,
) -> Dict[str, Any]:
    runtime = build_runtime(
        mode="web",
        enable_deep_review=enable_deep_review,
        paper_paths=[str(path)],
        template_name=req.template,
        review_track=req.review_track,
    )
    task = create_paper_task(
        path,
        depth="deep" if enable_deep_review else req.depth,
        template_name=req.template,
        review_track=req.review_track,
    )
    result = await execute_review_task(runtime, task, enable_deep_review=enable_deep_review)
    payload = build_review_payload(result, plan_id=runtime.plan.plan_id)
    payload["sections"]["structure"] = (
        result.format_check.get("structure", {}) if isinstance(result.format_check, dict) else {}
    )
    return _annotate_review_payload(payload, backend="local_runtime", warning=warning)


# ─── System ─────────────────────────────────────────────

@app.get("/api/status")
async def get_status():
    """系统状态检查"""
    from article_check.config.settings import config
    from article_check.rules.registry import template_registry

    registry_status = get_dify_registry_status()
    return api_success({
        "version": "0.3.0",
        "ai_provider": config.ai.provider,
        "dify_enabled": bool(registry_status.get("available")),
        "dify_registry": registry_status,
        "review_backend": "dify_workflow_chain" if registry_status.get("available") else "local_runtime",
        "templates": template_registry.count,
        "templates_list": [t.name for t in template_registry.list_all()],
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

    if dify_workflows_available():
        try:
            payload = await asyncio.to_thread(
                run_dify_review_chain,
                str(path),
                template_name=req.template,
                detailed_mode=bool(req.with_deep_review or req.depth == "deep"),
                review_track=req.review_track,
                review_focus=req.review_focus,
                report_focus=req.report_focus,
            )
            return api_success(_annotate_review_payload(payload, backend="dify_workflow_chain"))
        except Exception as exc:
            logger.exception("Dify 审查链执行失败")
            warning = f"Dify 审查链执行失败，已自动回退本地审查: {exc}"
            payload = await _run_local_review_payload(
                path,
                req,
                enable_deep_review=bool(req.with_deep_review or req.depth == "deep"),
                warning=warning,
            )
            return api_success(payload)

    payload = await _run_local_review_payload(
        path,
        req,
        enable_deep_review=bool(req.with_deep_review or req.depth == "deep"),
    )
    return api_success(payload)


@app.post("/api/review/deep")
async def deep_review(req: ReviewRequest):
    """深度审查（含 DeepSeek 内容分析）"""
    path = Path(req.paper_path)
    if not path.exists():
        raise HTTPException(404, "文件不存在")

    if dify_workflows_available():
        try:
            payload = await asyncio.to_thread(
                run_dify_review_chain,
                str(path),
                template_name=req.template,
                detailed_mode=True,
                review_track=req.review_track,
                review_focus=req.review_focus,
                report_focus=req.report_focus,
            )
            return api_success(_annotate_review_payload(payload, backend="dify_workflow_chain"))
        except Exception as exc:
            logger.exception("Dify 深度审查链执行失败")
            warning = f"Dify 深度审查链执行失败，已自动回退本地审查: {exc}"
            payload = await _run_local_review_payload(
                path,
                req,
                enable_deep_review=bool(req.with_deep_review),
                warning=warning,
            )
            return api_success(payload)

    payload = await _run_local_review_payload(path, req, enable_deep_review=bool(req.with_deep_review))
    return api_success(payload)


@app.post("/api/report/dialogue")
async def report_dialogue(req: ReportDialogueRequest):
    """围绕结构化报告进行问答。"""
    if dify_workflows_available():
        try:
            answer = await asyncio.to_thread(run_dify_report_qa, req.report_payload, req.question)
            return api_success({"answer": answer})
        except Exception:
            logger.exception("Dify 报告问答失败，将回退本地问答。")
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
    snippet = _read_text_excerpt(source_path, evidence.get("location") or {}, evidence, req.context_radius)
    return api_success({
        "evidence_id": req.evidence_id,
        "source_path": str(source_path),
        "source_name": source_path.name,
        "location": evidence.get("location") or {},
        "claim": evidence.get("claim") or "",
        "snippet": snippet,
    })


# ─── Stream Review (SSE) ───────────────────────────────

@app.post("/api/review/batch-stream")
async def batch_review_stream(req: BatchReviewRequest):
    """流式批量审查 — SSE 推送"""
    async def event_stream():
        paths = req.paths
        if dify_workflows_available():
            total = len(paths)
            yield f"data: {json.dumps({'type': 'start', 'total': total})}\n\n"
            for raw_path in paths:
                try:
                    payload = await asyncio.to_thread(
                        run_dify_review_chain,
                        raw_path,
                        template_name=req.template,
                        detailed_mode=bool(req.with_deep_review),
                        review_track=req.review_track,
                    )
                    data = {
                        "type": "result",
                        "paper_title": (payload.get("meta") or {}).get("paper_title"),
                        "score": (payload.get("meta") or {}).get("overall_score"),
                        "duration": (payload.get("meta") or {}).get("duration"),
                        "errors": payload.get("errors", []),
                        "report_path": (payload.get("summary") or {}).get("formal_report_markdown_path"),
                        "review_payload": _annotate_review_payload(payload, backend="dify_workflow_chain"),
                    }
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                except Exception as exc:
                    logger.exception("Dify 批量审查失败，回退本地 runtime: %s", raw_path)
                    path = Path(raw_path)
                    if not path.exists():
                        error_data = {
                            "type": "result",
                            "paper_title": path.stem,
                            "score": None,
                            "duration": None,
                            "errors": [f"文件不存在: {raw_path}"],
                            "report_path": None,
                            "review_payload": None,
                        }
                        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                        continue

                    fallback_req = ReviewRequest(
                        paper_path=raw_path,
                        depth="deep" if req.with_deep_review else "auto",
                        with_deep_review=bool(req.with_deep_review),
                        review_track=req.review_track,
                        template=req.template,
                    )
                    payload = await _run_local_review_payload(
                        path,
                        fallback_req,
                        enable_deep_review=bool(req.with_deep_review),
                        warning=f"Dify 批量审查失败，已自动回退本地审查: {exc}",
                    )
                    data = {
                        "type": "result",
                        "paper_title": (payload.get("meta") or {}).get("paper_title"),
                        "score": (payload.get("meta") or {}).get("overall_score"),
                        "duration": (payload.get("meta") or {}).get("duration"),
                        "errors": payload.get("errors", []),
                        "report_path": (payload.get("summary") or {}).get("formal_report_markdown_path"),
                        "review_payload": payload,
                    }
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            return

        runtime = build_runtime(
            mode="batch",
            enable_deep_review=bool(req.with_deep_review),
            enable_streaming=True,
            paper_paths=paths,
            template_name=req.template,
            review_track=req.review_track,
        )
        tasks = [
            create_paper_task(
                p,
                depth="deep" if req.with_deep_review else "auto",
                template_name=req.template,
                review_track=req.review_track,
            )
            for p in paths
        ]

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


# ─── Health / Static Files / SPA ───────────────────────

@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "article-check-api"}


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


def run_server(host: str = "127.0.0.1", port: int = 8765):
    """启动 Web 服务器"""
    import uvicorn
    print(f"🌐 Article Check Web UI: http://{host}:{port}")
    print(f"📚 API 文档: http://{host}:{port}/docs")
    print(f"🔍 按 Ctrl+C 停止")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
