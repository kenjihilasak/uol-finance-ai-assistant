"""FastAPI contract used by the public portfolio chat."""

from __future__ import annotations

import os
from typing import Annotated, Protocol

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from api.catalog import PublicDocument, load_document_catalog
from api.rate_limit import FixedWindowRateLimiter
from scripts.stage_05_retrieval.generate_grounded_answer import (
    Evidence,
    GroundedAnswer,
    load_config,
    run_grounded_answer,
)


DEFAULT_ALLOWED_ORIGINS = (
    "https://kenjihilasak.github.io",
    "http://localhost:4321",
)
MAX_PUBLIC_QUESTION_CHARACTERS = 500
catalog = load_document_catalog()


class DocumentResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: str
    title: str
    institution: str
    document_date: str
    source_url: str
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


def document_response(document: PublicDocument) -> DocumentResponse:
    return DocumentResponse(
        document_id=document.document_id,
        title=document.title,
        institution=document.institution,
        document_date=document.document_date.isoformat(),
        source_url=document.source_url,
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


app = FastAPI(
    title="UoL Finance AI Assistant API",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
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
