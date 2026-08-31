"""Validate and upload Stage 03 embedding records to Azure AI Search."""

from __future__ import annotations

import argparse
import json
import math
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from azure.search.documents import SearchClient
from dotenv import load_dotenv

from scripts.shared.azure_auth import build_user_credential
from scripts.shared.document_utils import PROJECT_ROOT


UPLOAD_BATCH_SIZE = 100
INDEX_FIELDS = {
    "chunk_id",
    "document_id",
    "text",
    "embedding_text",
    "source_title",
    "institution",
    "source_reference",
    "source_url",
    "status",
    "embedding_deployment",
    "page_number",
    "document_date",
    "source_sha256",
    "text_sha256",
    "embedding_text_sha256",
    "page_range",
    "character_range",
    "content_vector",
}


def require_string(record: dict[str, Any], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"{field} must be a non-empty string")
    return value


def datetime_offset(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise RuntimeError("document_date must be a non-empty ISO date string")

    try:
        if len(value) == 10:
            parsed = date.fromisoformat(value)
            return f"{parsed.isoformat()}T00:00:00Z"

        parsed_datetime = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise RuntimeError("document_date must be a valid ISO date") from error

    if parsed_datetime.tzinfo is None:
        parsed_datetime = parsed_datetime.replace(tzinfo=timezone.utc)
    return parsed_datetime.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def integer_range(record: dict[str, Any], field: str) -> dict[str, int]:
    value = record.get(field)
    if not isinstance(value, dict):
        raise RuntimeError(f"{field} must be an object")

    start = value.get("start")
    end = value.get("end")
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start < 0
        or end < start
    ):
        raise RuntimeError(f"{field} must contain a valid integer start/end range")
    return {"start": start, "end": end}


def embedding_vector(record: dict[str, Any], dimensions: int) -> list[float]:
    value = record.get("content_vector")
    if not isinstance(value, list) or len(value) != dimensions:
        raise RuntimeError(
            f"content_vector must contain exactly {dimensions} values"
        )

    vector: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise RuntimeError("content_vector values must be numeric")
        numeric_value = float(item)
        if not math.isfinite(numeric_value):
            raise RuntimeError("content_vector values must be finite")
        vector.append(numeric_value)
    return vector


def search_document(
    record: dict[str, Any],
    embedding_deployment: str,
    vector_dimensions: int,
) -> dict[str, Any]:
    """Map one pipeline record to the exact Azure Search index contract."""
    page_number = record.get("page_number")
    if not isinstance(page_number, int) or isinstance(page_number, bool):
        raise RuntimeError("page_number must be an integer")

    document: dict[str, Any] = {
        "chunk_id": require_string(record, "chunk_id"),
        "document_id": require_string(record, "document_id"),
        "text": require_string(record, "text"),
        "embedding_text": require_string(record, "embedding_text"),
        "source_title": require_string(record, "source_title"),
        "institution": require_string(record, "institution"),
        "source_reference": require_string(record, "source_reference"),
        "status": require_string(record, "status"),
        "embedding_deployment": embedding_deployment,
        "page_number": page_number,
        "document_date": datetime_offset(record.get("document_date")),
        "source_sha256": require_string(record, "source_sha256"),
        "text_sha256": require_string(record, "text_sha256"),
        "embedding_text_sha256": require_string(
            record, "embedding_text_sha256"
        ),
        "page_range": integer_range(record, "page_range"),
        "character_range": integer_range(record, "character_range"),
        "content_vector": embedding_vector(record, vector_dimensions),
    }

    source_url = record.get("source_url")
    if source_url is not None:
        if not isinstance(source_url, str) or not source_url:
            raise RuntimeError("source_url must be a non-empty string or null")
        document["source_url"] = source_url

    unexpected = document.keys() - INDEX_FIELDS
    if unexpected:
        raise RuntimeError(
            "Mapped document contains unknown index fields: "
            + ", ".join(sorted(unexpected))
        )
    return document


def load_search_documents(
    embeddings_file: Path,
) -> tuple[str, int, list[dict[str, Any]]]:
    if not embeddings_file.is_file():
        raise FileNotFoundError(f"Embeddings file not found: {embeddings_file}")

    payload = json.loads(embeddings_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Embeddings JSON must be an object")

    embedding_deployment = payload.get("embedding_deployment")
    dimensions = payload.get("embedding_dimensions")
    records = payload.get("records")
    if not isinstance(embedding_deployment, str) or not embedding_deployment:
        raise RuntimeError("Embedding payload is missing embedding_deployment")
    if not isinstance(dimensions, int) or isinstance(dimensions, bool):
        raise RuntimeError("Embedding payload has invalid embedding_dimensions")
    if not isinstance(records, list) or not records:
        raise RuntimeError("Embedding payload must contain non-empty records")

    documents: list[dict[str, Any]] = []
    chunk_ids: set[str] = set()
    for position, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise RuntimeError(f"Embedding record {position} must be an object")
        try:
            document = search_document(record, embedding_deployment, dimensions)
        except RuntimeError as error:
            raise RuntimeError(f"Invalid embedding record {position}: {error}") from error

        chunk_id = str(document["chunk_id"])
        if chunk_id in chunk_ids:
            raise RuntimeError(f"Duplicate chunk_id: {chunk_id}")
        chunk_ids.add(chunk_id)
        documents.append(document)

    return embedding_deployment, dimensions, documents


def upload_documents(
    service_endpoint: str,
    index_name: str,
    tenant_id: str,
    documents: list[dict[str, Any]],
) -> None:
    credential = build_user_credential(tenant_id)
    search_client = SearchClient(
        endpoint=service_endpoint,
        index_name=index_name,
        credential=credential,
    )

    uploaded = 0
    total_batches = (len(documents) + UPLOAD_BATCH_SIZE - 1) // UPLOAD_BATCH_SIZE
    try:
        for start in range(0, len(documents), UPLOAD_BATCH_SIZE):
            batch = documents[start : start + UPLOAD_BATCH_SIZE]
            batch_number = start // UPLOAD_BATCH_SIZE + 1
            results = search_client.upload_documents(documents=batch)
            failures = [result for result in results if not result.succeeded]
            if failures:
                details = "; ".join(
                    f"{result.key}: {result.error_message}" for result in failures
                )
                raise RuntimeError(
                    f"Azure rejected {len(failures)} documents in batch "
                    f"{batch_number}: {details}"
                )
            uploaded += len(results)
            print(
                f"Uploaded batch {batch_number}/{total_batches} "
                f"({uploaded}/{len(documents)} documents)",
                flush=True,
            )
    finally:
        search_client.close()
        credential.close()

    if uploaded != len(documents):
        raise RuntimeError(
            f"Upload count mismatch: expected {len(documents)}, received {uploaded}"
        )
    print(f"Uploaded and verified {uploaded} documents to index '{index_name}'.")


def load_config() -> tuple[str, str]:
    load_dotenv(PROJECT_ROOT / ".env")
    service_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    tenant_id = os.getenv("AZURE_TENANT_ID")
    missing = [
        name
        for name, value in (
            ("AZURE_SEARCH_ENDPOINT", service_endpoint),
            ("AZURE_TENANT_ID", tenant_id),
        )
        if not value or str(value).startswith("<")
    ]
    if missing:
        raise RuntimeError("Missing local configuration: " + ", ".join(missing))
    return str(service_endpoint).rstrip("/"), str(tenant_id)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload validated embedding records to Azure AI Search."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--index-name", required=True)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and map every record without contacting Azure.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    service_endpoint, tenant_id = load_config()
    deployment, dimensions, documents = load_search_documents(args.input)

    if args.dry_run:
        print("Search upload dry run passed")
        print(f"Index: {args.index_name}")
        print(f"Documents validated: {len(documents)}")
        print(f"Embedding deployment: {deployment}")
        print(f"Vector dimensions: {dimensions}")
        print("Azure authentication and document upload: not performed")
        return

    upload_documents(
        service_endpoint,
        args.index_name,
        tenant_id,
        documents,
    )


if __name__ == "__main__":
    main()
