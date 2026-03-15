from __future__ import annotations

import mimetypes
import logging
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.config import settings
from app.schemas import (
    AnalysisRunRequest,
    HomeworkApproval,
    OcrNormalizeRequest,
    OcrRunRequest,
    ProblemRegradeRequest,
    ProblemRegradeResponse,
    RagHomeworkRequest,
    StudentDocumentCreateRequest,
    StudentOverviewResponse,
    UploadResponse,
)
from app.services.analysis import AnalysisService
from app.services.data_store import load_catalog, load_students
from app.services.llm_sheet_ocr import extract_llm_ocr_document
from app.services.ocr_normalizer import build_ocr_debug_artifact, normalize_ocr_result, persist_ocr_debug_artifact
from app.services.student_summary import build_fallback_summary, build_rag_homework_recommendation
from app.storage.repository import Repository

router = APIRouter(prefix="/api")
logger = logging.getLogger("uvicorn.error")
repo = Repository()
analysis_service = AnalysisService()


def _find_student(student_id: str):
    student = repo.get_student(student_id)
    if student is not None:
        return student
    raise HTTPException(status_code=404, detail="Student not found")


def _refresh_summary(student_id: str, generation_mode: str = "manual") -> dict:
    student = _find_student(student_id)
    metrics = repo.list_student_metrics(student_id)
    documents = repo.list_student_documents(student_id)
    if not documents:
        raise HTTPException(status_code=404, detail="Student documents not found")
    query = " ".join(student.weakness_history + [student.persona_summary])
    chunks = repo.search_rag_chunks(student_id, query, limit=8)
    summary = build_fallback_summary(student, metrics, chunks, documents)
    repo.save_student_summary(summary, generation_mode=generation_mode)
    return summary.model_dump(mode="json")


def _resolve_upload_path(source_image_id: str) -> Path:
    matches = list(settings.upload_dir.glob(f"{source_image_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Uploaded image not found")
    return matches[0]


def _resolve_source_image_ids(request: OcrRunRequest) -> list[str]:
    if request.source_image_ids:
        return request.source_image_ids
    if request.source_image_id:
        return [request.source_image_id]
    raise HTTPException(status_code=422, detail="source_image_id or source_image_ids is required")


def _merge_raw_ocr_results(raw_docs: list[dict]) -> dict:
    return {"documents": raw_docs}


def _attach_source_paths(normalized, upload_paths: list[Path]) -> None:
    relative_paths = [str(path.relative_to(settings.repo_root)) for path in upload_paths]
    normalized.source_image_paths = relative_paths
    primary = relative_paths[0] if relative_paths else None
    for item in normalized.items:
        item.source_image_path = primary


def _merge_normalized_documents(documents: list[tuple[Path, dict, object]]) -> tuple[dict, object, dict]:
    raw_docs = [entry[1] for entry in documents]
    normalized_docs = [entry[2] for entry in documents]
    first = normalized_docs[0]
    merged_items = []
    seen_problem_nos: set[str] = set()
    source_paths: list[str] = []
    test_id = first.test_id
    source_alias = first.source_alias
    confidence_notes: list[str] = []
    low_confidence_count = 0
    for normalized in normalized_docs:
        source_paths.extend(normalized.source_image_paths)
        if not test_id and normalized.test_id:
            test_id = normalized.test_id
        if not source_alias and normalized.source_alias:
            source_alias = normalized.source_alias
        low_confidence_count += normalized.ocr_confidence_summary.low_confidence_count
        confidence_notes.extend(normalized.ocr_confidence_summary.notes)
        for item in normalized.items:
            if item.problem_no in seen_problem_nos:
                continue
            merged_items.append(item)
            seen_problem_nos.add(item.problem_no)
    merged_items.sort(key=lambda item: int(item.problem_no[1:]) if item.problem_no[1:].isdigit() else item.problem_no)
    merged = first.model_copy(deep=True)
    merged.source_image_paths = source_paths
    merged.items = merged_items
    merged.test_id = test_id
    merged.source_alias = source_alias
    merged.ocr_confidence_summary.low_confidence_count = low_confidence_count
    merged.ocr_confidence_summary.notes = confidence_notes
    debug_payload = {
        "mode": "llm_ocr_batch",
        "documents": raw_docs,
        "normalized": merged.model_dump(),
    }
    return _merge_raw_ocr_results(raw_docs), merged, debug_payload


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/students")
def get_students() -> list[dict]:
    return [student.model_dump() for student in load_students()]


@router.get("/students/overview")
def get_students_overview() -> dict:
    items = repo.build_overview_items()
    if not all(item.one_line_analysis for item in items):
        for student in load_students():
            if repo.get_latest_student_summary(student.student_id) is None:
                _refresh_summary(student.student_id, generation_mode="bootstrap")
        items = repo.build_overview_items()
    payload = StudentOverviewResponse(
        total_students=len(items),
        urgent_count=sum(1 for item in items if item.attention_level in {"high", "urgent"}),
        low_completion_count=sum(1 for item in items if item.homework_completion_rate < 60),
        counseling_priority_count=sum(1 for item in items if item.attention_level == "urgent"),
        recommended_actions_today=sum(1 for item in items if item.recommended_action),
        students=items,
    )
    return payload.model_dump()


@router.get("/students/{student_id}")
def get_student(student_id: str) -> dict:
    return _find_student(student_id).model_dump()


@router.get("/students/{student_id}/summary")
def get_student_summary(student_id: str) -> dict:
    _find_student(student_id)
    summary = repo.get_latest_student_summary(student_id)
    if summary is None:
        return _refresh_summary(student_id, generation_mode="bootstrap")
    return summary.model_dump(mode="json")


@router.post("/students/{student_id}/refresh-summary")
def refresh_student_summary(student_id: str) -> dict:
    return _refresh_summary(student_id, generation_mode="manual")


@router.get("/students/{student_id}/documents")
def get_student_documents(student_id: str) -> list[dict]:
    _find_student(student_id)
    return [document.model_dump(mode="json") for document in repo.list_student_documents(student_id)]


@router.post("/students/{student_id}/documents")
def create_student_document(student_id: str, payload: StudentDocumentCreateRequest) -> dict:
    _find_student(student_id)
    document = repo.add_student_document(student_id, payload)
    _refresh_summary(student_id, generation_mode="document_update")
    return document.model_dump(mode="json")


@router.get("/students/{student_id}/homework-history")
def get_student_homework_history(student_id: str) -> list[dict]:
    _find_student(student_id)
    return [item.model_dump(mode="json") for item in repo.list_homework_history(student_id)]


@router.get("/catalog")
def get_catalog() -> list[dict]:
    return [problem.model_dump() for problem in load_catalog()]


@router.get("/demo/{student_id}/replay")
def get_replay_snapshot(student_id: str) -> dict:
    _find_student(student_id)
    replay_path = settings.data_dir / "replays" / f"{student_id}.json"
    if not replay_path.exists():
        raise HTTPException(status_code=404, detail="Replay snapshot not found for this student")
    return json.loads(replay_path.read_text())


@router.post("/uploads")
async def upload_file(student_id: str = Form(...), file: UploadFile = File(...)) -> dict:
    _find_student(student_id)
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large. Keep it under 5MB.")
    source_image_id = f"img-{uuid4().hex[:12]}"
    suffix = Path(file.filename or "upload.bin").suffix or ".bin"
    filename = f"{source_image_id}{suffix}"
    stored_path = settings.upload_dir / filename
    stored_path.write_bytes(content)
    upload = UploadResponse(
        source_image_id=source_image_id,
        filename=file.filename or filename,
        stored_path=str(stored_path.relative_to(settings.repo_root)),
        source_mode="live",
    )
    repo.save_upload(student_id, upload)
    return upload.model_dump()


@router.post("/ocr/run")
async def run_ocr(request: OcrRunRequest) -> dict:
    student = _find_student(request.student_id)
    source_image_ids = _resolve_source_image_ids(request)
    upload_paths = [_resolve_upload_path(source_image_id) for source_image_id in source_image_ids]
    normalized_source_id = source_image_ids[0] if len(source_image_ids) == 1 else f"batch-{source_image_ids[0]}-{len(source_image_ids)}"
    llm_documents = []
    try:
        for source_image_id, upload_path in zip(source_image_ids, upload_paths, strict=True):
            source_relpath = str(upload_path.relative_to(settings.repo_root))
            raw_payload, normalized_doc, debug_payload = await extract_llm_ocr_document(
                image_path=upload_path,
                student_id=student.student_id,
                source_image_id=source_image_id,
                source_image_relpath=source_relpath,
                aoai_client=analysis_service.client,
            )
            timing = debug_payload.get("timing_ms", {})
            logger.info(
                "OCR stage timing: source_image_id=%s layout_ms=%s reading_ms=%s total_ms=%s",
                source_image_id,
                timing.get("layout_pass"),
                timing.get("reading_pass"),
                timing.get("total_ocr"),
            )
            llm_documents.append(
                (
                    upload_path,
                    raw_payload,
                    normalized_doc,
                    debug_payload,
                )
            )
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        if status_code == 429:
            raise HTTPException(
                status_code=503,
                detail="AI OCR is temporarily busy. Please wait about 30 seconds and try again.",
            ) from exc
        raise HTTPException(status_code=502, detail="AI OCR failed. Please try again.") from exc
    raw_ocr, normalized, debug_payload = _merge_normalized_documents([(path, raw_payload, doc) for path, raw_payload, doc, _ in llm_documents])
    if len(llm_documents) == 1:
        debug_payload = llm_documents[0][3]
        raw_ocr = llm_documents[0][1]
        normalized = llm_documents[0][2]
    debug_artifact = persist_ocr_debug_artifact(normalized_source_id, debug_payload)
    logger.info(
        "OCR debug saved: source_image_id=%s test_id=%s items=%s path=%s",
        normalized_source_id,
        normalized.test_id,
        len(normalized.items),
        debug_artifact,
    )
    return {
        "source_mode": "live",
        "raw_ocr": raw_ocr,
        "normalized_ocr": normalized.model_dump(),
        "debug_artifact_path": str(debug_artifact.relative_to(settings.repo_root)),
    }


@router.post("/ocr/normalize")
def normalize_ocr(request: OcrNormalizeRequest) -> dict:
    normalized = normalize_ocr_result(request.raw_ocr, request.student_id, request.source_image_id)
    debug_payload = build_ocr_debug_artifact(request.raw_ocr, request.student_id, request.source_image_id)
    debug_payload["normalized"] = normalized.model_dump()
    debug_artifact = persist_ocr_debug_artifact(request.source_image_id, debug_payload)
    logger.info(
        "OCR debug saved: source_image_id=%s test_id=%s items=%s path=%s",
        request.source_image_id,
        normalized.test_id,
        len(normalized.items),
        debug_artifact,
    )
    payload = normalized.model_dump()
    payload["debug_artifact_path"] = str(debug_artifact.relative_to(settings.repo_root))
    return payload


@router.post("/analysis/run")
async def run_analysis(request: AnalysisRunRequest) -> dict:
    started = datetime.now(timezone.utc)
    student = _find_student(request.student_id)
    catalog = load_catalog()
    analysis = await analysis_service.run(student, request.normalized_ocr, catalog, mode=request.mode, action=request.action)
    logger.info(
        "Analysis timing: student_id=%s mode=%s elapsed_ms=%.1f",
        request.student_id,
        "live",
        (datetime.now(timezone.utc) - started).total_seconds() * 1000,
    )
    return analysis.model_dump()


@router.post("/analysis/regrade-problem")
async def regrade_problem(request: ProblemRegradeRequest) -> dict:
    _find_student(request.student_id)
    if not request.normalized_ocr.test_id:
        raise HTTPException(status_code=422, detail="Problem regrade is available only for confirmation tests")
    if request.current_analysis is not None:
        analysis = request.current_analysis
    else:
        catalog = load_catalog()
        analysis = await analysis_service.run(
            _find_student(request.student_id),
            request.normalized_ocr,
            catalog,
            mode="live",
            action="initial",
        )
    try:
        updated_analysis, updated_problem = analysis_service.regrade_problem(
            analysis,
            request.normalized_ocr,
            request.problem_no,
            request.student_note,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Problem not found: {request.problem_no}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    response = ProblemRegradeResponse(problem_feedback=updated_problem, analysis=updated_analysis)
    return response.model_dump()


@router.post("/homework/approve")
def approve_homework(payload: HomeworkApproval) -> dict:
    approval = repo.save_approval(payload)
    return approval.model_dump(mode="json")


@router.post("/homework/rag-recommend")
async def rag_recommend_homework(payload: RagHomeworkRequest) -> dict:
    student = _find_student(payload.student_id)
    summary = repo.get_latest_student_summary(payload.student_id)
    if summary is None:
        summary = build_fallback_summary(
            student,
            repo.list_student_metrics(payload.student_id),
            repo.search_rag_chunks(payload.student_id, " ".join(student.weakness_history), limit=8),
            repo.list_student_documents(payload.student_id),
        )
        repo.save_student_summary(summary, generation_mode="rag-homework")
    recommendation = build_rag_homework_recommendation(
        student=student,
        metrics=repo.list_student_metrics(payload.student_id),
        summary=summary,
        homework_history=repo.list_homework_history(payload.student_id),
        catalog=load_catalog(),
        analysis=payload.analysis,
        normalized_ocr=payload.normalized_ocr,
    )
    return recommendation.model_dump(mode="json")
