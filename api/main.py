"""FastAPI contract used by the public portfolio chat."""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Protocol
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from dotenv import load_dotenv

from api.catalog import PublicDocument, load_document_catalog
from api.enquiries import EnquiryRepository
from api.rate_limit import FixedWindowRateLimiter
from api.staff_auth import StaffIdentity, require_staff
from scripts.stage_05_retrieval.generate_grounded_answer import (
    Evidence,
    GroundedAnswer,
    load_config,
    run_grounded_answer,
)
from scripts.stage_06_triage.schemas import TriageDecision
from scripts.stage_06_triage.triage_enquiry import TriageOutcome, run_default_triage


DEFAULT_ALLOWED_ORIGINS = (
    "https://kenjihilasak.github.io",
    "http://localhost:4321",
)
MAX_PUBLIC_QUESTION_CHARACTERS = 500
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
catalog = load_document_catalog()
enquiry_repository = EnquiryRepository()


class DocumentResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: str
    title: str
    institution: str
    category: str
    document_date: str
    source_url: str
    content_type: str
    status: str
    suggested_questions: list[str]


class AnswerRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    question: str = Field(min_length=3, max_length=MAX_PUBLIC_QUESTION_CHARACTERS)
    document_id: str = Field(min_length=1, max_length=300)


class CitationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    chunk_id: str
    title: str
    page_number: int
    source_url: str
    page_url: str
    excerpt: str


class AnswerResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    answer: str
    citations: list[CitationResponse]


class TriageRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    enquiry: str = Field(min_length=3, max_length=4_000)
    persist: bool = False


class StaffTriageRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    enquiry: str = Field(min_length=3, max_length=4_000)


class TriageResponse(BaseModel):
    enquiry_id: str
    decision: TriageDecision
    answer_status: str | None
    draft_response: str | None
    citations: list[CitationResponse]
    review_status: str


class ReviewRequest(BaseModel):
    review_status: str = Field(pattern="^(approved|edited|clarification_sent|routed|rejected)$")


class AnswerService(Protocol):
    def answer(
        self,
        question: str,
        document_id: str,
    ) -> tuple[GroundedAnswer, list[Evidence]]: ...


class AzureAnswerService:
    def answer(
        self,
        question: str,
        document_id: str,
    ) -> tuple[GroundedAnswer, list[Evidence]]:
        if os.getenv("API_LIVE_ENABLED", "false").strip().lower() != "true":
            raise RuntimeError("Live model calls are disabled")
        return run_grounded_answer(
            load_config(),
            question,
            top=5,
            vector_candidates=50,
            document_id=document_id,
        )


class TriageService(Protocol):
    def triage(self, enquiry: str) -> TriageOutcome: ...


class AzureTriageService:
    def triage(self, enquiry: str) -> TriageOutcome:
        if os.getenv("API_LIVE_ENABLED", "false").strip().lower() != "true":
            raise RuntimeError("Live model calls are disabled")
        return run_default_triage(enquiry)


def get_triage_service() -> TriageService:
    return AzureTriageService()


def get_answer_service() -> AnswerService:
    return AzureAnswerService()


def configured_origins() -> list[str]:
    raw_value = os.getenv("API_ALLOWED_ORIGINS")
    if not raw_value:
        return list(DEFAULT_ALLOWED_ORIGINS)
    origins = [origin.strip().rstrip("/") for origin in raw_value.split(",")]
    return [origin for origin in origins if origin]


def configured_rate_limit() -> int:
    raw_value = os.getenv("API_MAX_REQUESTS_PER_MINUTE", "5")
    try:
        value = int(raw_value)
    except ValueError as error:
        raise RuntimeError("API_MAX_REQUESTS_PER_MINUTE must be an integer") from error
    if not 1 <= value <= 120:
        raise RuntimeError("API_MAX_REQUESTS_PER_MINUTE must be between 1 and 120")
    return value


def require_admin(request: Request) -> None:
    expected = os.getenv("API_ADMIN_TOKEN")
    supplied = request.headers.get("X-Admin-Token")
    if not expected or not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(403, "Admin access required")


def document_response(document: PublicDocument) -> DocumentResponse:
    return DocumentResponse(
        document_id=document.document_id,
        title=document.title,
        institution=document.institution,
        category=document.category,
        document_date=document.document_date.isoformat(),
        source_url=document.source_url,
        content_type=document.content_type,
        status=document.status,
        suggested_questions=list(document.suggested_questions),
    )


def answer_response(
    answer: GroundedAnswer,
    evidence: list[Evidence],
    document: PublicDocument,
) -> AnswerResponse:
    evidence_by_id = {item.source_id: item for item in evidence}
    citations = []
    for source_id in answer.citation_ids:
        item = evidence_by_id[source_id]
        citations.append(
            CitationResponse(
                source_id=source_id,
                chunk_id=item.chunk_id,
                title=item.title,
                page_number=item.page_number,
                source_url=document.source_url,
                page_url=document.page_url(item.page_number),
                excerpt=item.text[:600],
            )
        )
    return AnswerResponse(
        status=answer.status,
        answer=answer.answer,
        citations=citations,
    )


def document_for_evidence(item: Evidence) -> PublicDocument:
    matches = [doc for document_id, doc in catalog.items() if item.chunk_id.startswith(document_id)]
    if not matches:
        raise RuntimeError(f"Evidence source is not in the public catalog: {item.chunk_id}")
    return matches[0]


def triage_response(
    enquiry: str,
    outcome: TriageOutcome,
    *,
    persist: bool,
    staff: StaffIdentity | None = None,
) -> TriageResponse:
    enquiry_id = str(uuid4())
    evidence_by_id = {item.source_id: item for item in outcome.evidence}
    citation_ids = outcome.answer.citation_ids if outcome.answer else ()
    citations: list[CitationResponse] = []
    for source_id in citation_ids:
        item = evidence_by_id[source_id]
        document = document_for_evidence(item)
        citations.append(CitationResponse(
            source_id=source_id, chunk_id=item.chunk_id, title=item.title,
            page_number=item.page_number, source_url=document.source_url,
            page_url=document.page_url(item.page_number), excerpt=item.text[:600],
        ))
    response = TriageResponse(
        enquiry_id=enquiry_id,
        decision=outcome.decision,
        answer_status=outcome.answer.status if outcome.answer else None,
        draft_response=outcome.answer.answer if outcome.answer else None,
        citations=citations,
        review_status="pending",
    )
    classification = outcome.decision.classification
    record = {
        "enquiry_id": enquiry_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "enquiry": enquiry,
        "summary": classification.summary,
        "category": classification.category.value,
        "subcategory": classification.subcategory,
        "is_sensitive": classification.is_sensitive or bool(outcome.decision.rule_flags),
        "action": outcome.decision.action.value,
        "route_to": outcome.decision.route_to.value,
        "missing_info": list(classification.missing_info),
        "answer_status": response.answer_status,
        "draft_response": response.draft_response,
        "citation_ids": list(citation_ids),
        "review_status": response.review_status,
        "staff_object_id": staff.object_id if staff else None,
        "staff_display_name": staff.display_name if staff else None,
    }
    if persist:
        enquiry_repository.save(record)
    return response


app = FastAPI(
    title="Agentic Support Intelligence API",
    version="2.0.0",
    docs_url=None,
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Token"],
)
limiter = FixedWindowRateLimiter(configured_rate_limit())


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/documents", response_model=list[DocumentResponse])
def list_documents() -> list[DocumentResponse]:
    return [document_response(document) for document in catalog.values()]


@app.post("/v1/answer", response_model=AnswerResponse)
async def answer_question(
    payload: AnswerRequest,
    request: Request,
    service: Annotated[AnswerService, Depends(get_answer_service)],
) -> AnswerResponse:
    document = catalog.get(payload.document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Unknown document_id")
    if document.status != "current":
        raise HTTPException(
            status_code=409,
            detail="Document is not ready for grounded answers",
        )

    client_key = request.client.host if request.client else "unknown"
    allowed, retry_after = limiter.allow(client_key)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests; try again later",
            headers={"Retry-After": str(retry_after)},
        )

    try:
        grounded_answer, evidence = await run_in_threadpool(
            service.answer,
            payload.question,
            payload.document_id,
        )
    except RuntimeError as error:
        if str(error) == "Live model calls are disabled":
            raise HTTPException(status_code=503, detail=str(error)) from error
        raise HTTPException(
            status_code=502,
            detail="The grounded-answer service is temporarily unavailable",
        ) from error
    return answer_response(grounded_answer, evidence, document)


@app.post("/v1/triage", response_model=TriageResponse)
async def triage_enquiry(
    payload: TriageRequest,
    request: Request,
    service: Annotated[TriageService, Depends(get_triage_service)],
) -> TriageResponse:
    if payload.persist:
        require_admin(request)
    client_key = request.client.host if request.client else "unknown"
    allowed, retry_after = limiter.allow(client_key)
    if not allowed:
        raise HTTPException(429, "Too many requests; try again later", headers={"Retry-After": str(retry_after)})
    try:
        outcome = await run_in_threadpool(service.triage, payload.enquiry)
        return triage_response(payload.enquiry, outcome, persist=payload.persist)
    except RuntimeError as error:
        if str(error) == "Live model calls are disabled":
            raise HTTPException(503, str(error)) from error
        raise HTTPException(502, "The triage service is temporarily unavailable") from error


@app.post("/v1/staff/triage", response_model=TriageResponse)
async def staff_triage_enquiry(
    payload: StaffTriageRequest,
    request: Request,
    staff: Annotated[StaffIdentity, Depends(require_staff)],
    service: Annotated[TriageService, Depends(get_triage_service)],
) -> TriageResponse:
    allowed, retry_after = limiter.allow(f"staff:{staff.object_id}")
    if not allowed:
        raise HTTPException(429, "Too many requests; try again later", headers={"Retry-After": str(retry_after)})
    try:
        outcome = await run_in_threadpool(service.triage, payload.enquiry)
        return triage_response(payload.enquiry, outcome, persist=True, staff=staff)
    except RuntimeError as error:
        if str(error) == "Live model calls are disabled":
            raise HTTPException(503, str(error)) from error
        raise HTTPException(502, "The triage service is temporarily unavailable") from error


@app.get("/v1/enquiries")
def list_enquiries(request: Request, limit: int = 50) -> list[dict[str, object]]:
    require_admin(request)
    return enquiry_repository.list(max(1, min(limit, 100)))


@app.patch("/v1/enquiries/{enquiry_id}")
def review_enquiry(enquiry_id: str, payload: ReviewRequest, request: Request) -> dict[str, str]:
    require_admin(request)
    if not enquiry_repository.update_review(enquiry_id, payload.review_status):
        raise HTTPException(404, "Unknown enquiry_id")
    return {"enquiry_id": enquiry_id, "review_status": payload.review_status}


@app.get("/v1/enquiries/export.xlsx")
def export_enquiries(request: Request) -> Response:
    require_admin(request)
    return Response(
        enquiry_repository.export_xlsx(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=triage-enquiries.xlsx"},
    )


@app.get("/v1/staff/enquiries")
def list_staff_enquiries(
    staff: Annotated[StaffIdentity, Depends(require_staff)],
    limit: int = 100,
) -> list[dict[str, object]]:
    return enquiry_repository.list(max(1, min(limit, 500)))


@app.patch("/v1/staff/enquiries/{enquiry_id}")
def review_staff_enquiry(
    enquiry_id: str,
    payload: ReviewRequest,
    staff: Annotated[StaffIdentity, Depends(require_staff)],
) -> dict[str, str]:
    if not enquiry_repository.update_review(enquiry_id, payload.review_status):
        raise HTTPException(404, "Unknown enquiry_id")
    return {"enquiry_id": enquiry_id, "review_status": payload.review_status}


@app.get("/v1/staff/enquiries/export.xlsx")
def export_staff_enquiries(
    staff: Annotated[StaffIdentity, Depends(require_staff)],
) -> Response:
    return Response(
        enquiry_repository.export_xlsx(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=triage-enquiries.xlsx"},
    )
