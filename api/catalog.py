"""Validated public metadata for documents exposed by the API."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from scripts.shared.document_utils import PROJECT_ROOT


CATALOG_PATH = PROJECT_ROOT / "config" / "public_documents.json"


@dataclass(frozen=True)
class PublicDocument:
    document_id: str
    title: str
    institution: str
    document_date: date
    source_url: str
    status: str
    suggested_questions: tuple[str, ...]

    def page_url(self, page_number: int) -> str:
        return f"{self.source_url}#page={page_number}"


def _required_text(item: dict[str, object], name: str) -> str:
    value = item.get(name)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"Document catalog field {name} must be non-empty text")
    return value.strip()


def load_document_catalog(path: Path = CATALOG_PATH) -> dict[str, PublicDocument]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1.0.0":
        raise RuntimeError("Unsupported public document catalog schema")
    items = payload.get("documents")
    if not isinstance(items, list) or not items:
        raise RuntimeError("Public document catalog must contain documents")

    catalog: dict[str, PublicDocument] = {}
    for raw_item in items:
        if not isinstance(raw_item, dict):
            raise RuntimeError("Each public document must be an object")
        document_id = _required_text(raw_item, "document_id")
        if document_id in catalog:
            raise RuntimeError(f"Duplicate public document: {document_id}")
        source_url = _required_text(raw_item, "source_url")
        parsed_url = urlparse(source_url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise RuntimeError("Public document source_url must use HTTPS")
        questions = raw_item.get("suggested_questions")
        if (
            not isinstance(questions, list)
            or not questions
            or any(
                not isinstance(question, str) or not question.strip()
                for question in questions
            )
        ):
            raise RuntimeError("suggested_questions must contain non-empty text")
        try:
            document_date = date.fromisoformat(
                _required_text(raw_item, "document_date")
            )
        except ValueError as error:
            raise RuntimeError("document_date must use YYYY-MM-DD") from error

        catalog[document_id] = PublicDocument(
            document_id=document_id,
            title=_required_text(raw_item, "title"),
            institution=_required_text(raw_item, "institution"),
            document_date=document_date,
            source_url=source_url,
            status=_required_text(raw_item, "status"),
            suggested_questions=tuple(question.strip() for question in questions),
        )
    return catalog
