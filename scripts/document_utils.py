from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = PROJECT_ROOT / "data" / "sources"
PROCESSED_DIRECTORY = PROJECT_ROOT / "data" / "processed"

SOURCE_METADATA_SCHEMA_VERSION = "1.0.0"
MAX_SOURCE_BYTES = 50 * 1024 * 1024
ALLOWED_DOCUMENT_STATUSES = {"current", "historical"}

REQUIRED_SOURCE_METADATA_FIELDS = {
    "schema_version",
    "document_id",
    "title",
    "institution",
    "document_date",
    "registered_at_utc",
    "sha256",
    "content_type",
    "status",
    "size_bytes",
    "local_filename",
    "blob_name",
    "source_reference",
    "source_url",
    "usage_basis",
    "rights_note",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def slugify(value: str, max_length: int = 96) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode(
        "ascii", "ignore"
    ).decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    slug = slug[:max_length].rstrip("-")
    if not slug:
        raise ValueError("The value cannot be converted to a safe identifier")
    return slug


def validate_document_id(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,127}", value):
        raise ValueError(
            "document_id must contain 3-128 lowercase letters, numbers, or hyphens"
        )
    return value


def validate_iso_date(value: str) -> str:
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("document_date must use YYYY-MM-DD") from error
    return value


def validate_optional_source_url(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("source_url must be an absolute HTTP or HTTPS URL")
    return candidate


def resolve_source_pdf(value: str | Path) -> Path:
    raw_path = Path(value).expanduser()
    candidate = raw_path if raw_path.is_absolute() else PROJECT_ROOT / raw_path

    if candidate.is_symlink():
        raise ValueError("Symbolic links are not accepted as source documents")

    resolved = candidate.resolve(strict=True)
    source_root = SOURCE_DIRECTORY.resolve()

    try:
        resolved.relative_to(source_root)
    except ValueError as error:
        raise ValueError(
            f"Source PDFs must be inside {SOURCE_DIRECTORY}"
        ) from error

    if not resolved.is_file():
        raise ValueError(f"The source path is not a regular file: {resolved}")
    if resolved.suffix.lower() != ".pdf":
        raise ValueError("The source file must have a .pdf extension")

    return resolved


def metadata_path_for(pdf_path: Path) -> Path:
    return pdf_path.with_suffix(".metadata.json")


def validate_pdf_file(
    pdf_path: Path, max_bytes: int = MAX_SOURCE_BYTES
) -> dict[str, int | str]:
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Source PDF not found: {pdf_path}")

    size_bytes = pdf_path.stat().st_size
    if size_bytes == 0:
        raise ValueError("The source PDF is empty")
    if size_bytes > max_bytes:
        raise ValueError(
            f"The source PDF exceeds the {max_bytes // (1024 * 1024)} MiB limit"
        )

    with pdf_path.open("rb") as source:
        if source.read(5) != b"%PDF-":
            raise ValueError(
                "The file does not start with the PDF format signature (%PDF-)"
            )

    return {
        "size_bytes": size_bytes,
        "sha256": sha256_file(pdf_path),
        "content_type": "application/pdf",
    }


def processed_path(document_id: str, artefact: str) -> Path:
    validate_document_id(document_id)
    if artefact not in {"processed", "chunks", "embeddings"}:
        raise ValueError(f"Unsupported processed artefact: {artefact}")
    return PROCESSED_DIRECTORY / f"{document_id}.{artefact}.json"


def load_and_verify_source(pdf_path: Path) -> dict[str, object]:
    metadata_path = metadata_path_for(pdf_path)
    if not metadata_path.is_file():
        raise FileNotFoundError(
            "Source metadata not found. Register the PDF first with "
            f"scripts/register_source_pdf.py: {metadata_path}"
        )

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise RuntimeError("Source metadata must be a JSON object")

    missing = REQUIRED_SOURCE_METADATA_FIELDS - metadata.keys()
    if missing:
        raise RuntimeError(
            "Missing source metadata fields: " + ", ".join(sorted(missing))
        )

    if metadata["schema_version"] != SOURCE_METADATA_SCHEMA_VERSION:
        raise RuntimeError(
            "Unsupported source metadata schema version: "
            f"{metadata['schema_version']}"
        )
    validate_document_id(str(metadata["document_id"]))
    validate_iso_date(str(metadata["document_date"]))

    non_empty_string_fields = (
        "title",
        "institution",
        "registered_at_utc",
        "local_filename",
        "blob_name",
        "source_reference",
        "usage_basis",
    )
    for field in non_empty_string_fields:
        if not isinstance(metadata[field], str) or not metadata[field].strip():
            raise RuntimeError(f"Source metadata field must be non-empty: {field}")

    source_url = metadata["source_url"]
    if source_url is not None and not isinstance(source_url, str):
        raise RuntimeError("source_url must be a string or null")
    validate_optional_source_url(source_url)

    rights_note = metadata["rights_note"]
    if rights_note is not None and not isinstance(rights_note, str):
        raise RuntimeError("rights_note must be a string or null")

    source_sha256 = metadata["sha256"]
    if not isinstance(source_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", source_sha256
    ):
        raise RuntimeError("Source metadata SHA-256 must be 64 lowercase hex digits")

    size_bytes = metadata["size_bytes"]
    if not isinstance(size_bytes, int) or isinstance(size_bytes, bool):
        raise RuntimeError("Source metadata size_bytes must be an integer")

    if metadata["status"] not in ALLOWED_DOCUMENT_STATUSES:
        raise RuntimeError(f"Unsupported document status: {metadata['status']}")
    if metadata["local_filename"] != pdf_path.name:
        raise RuntimeError("Metadata local_filename does not match the PDF")

    file_details = validate_pdf_file(pdf_path)
    if metadata["size_bytes"] != file_details["size_bytes"]:
        raise RuntimeError("Source PDF size does not match its metadata")
    if metadata["sha256"] != file_details["sha256"]:
        raise RuntimeError("Source PDF SHA-256 does not match its metadata")
    if metadata["content_type"] != file_details["content_type"]:
        raise RuntimeError("Source PDF content type does not match its metadata")

    return metadata
