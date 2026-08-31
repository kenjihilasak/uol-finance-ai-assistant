"""Run hybrid BM25 and vector retrieval against Azure AI Search."""

from __future__ import annotations

import argparse
import math
import os
import textwrap
from dataclasses import dataclass
from typing import Any

from azure.identity import get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from dotenv import load_dotenv
from openai import OpenAI

from scripts.shared.azure_auth import build_user_credential
from scripts.shared.document_utils import PROJECT_ROOT


OPENAI_SCOPE = "https://ai.azure.com/.default"
MAX_QUERY_CHARACTERS = 2_000
MAX_RESULTS = 20
MAX_VECTOR_CANDIDATES = 1_000
DEFAULT_TOP = 5
DEFAULT_VECTOR_CANDIDATES = 50
SEARCH_FIELDS = ["text", "source_title", "institution"]

# Never retrieve content_vector. The deployed v1 index exposes it, and returning a
# 1,536-float vector for every result wastes bandwidth and can leak into prompts.
SELECT_FIELDS = [
    "chunk_id",
    "document_id",
    "text",
    "source_title",
    "institution",
    "page_number",
    "document_date",
    "source_reference",
    "source_url",
    "status",
]


@dataclass(frozen=True)
class RetrievalConfig:
    tenant_id: str
    openai_endpoint: str
    embedding_deployment: str
    embedding_dimensions: int
    search_endpoint: str
    search_index_name: str


def load_config() -> RetrievalConfig:
    load_dotenv(PROJECT_ROOT / ".env")
    required_names = (
        "AZURE_TENANT_ID",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_EMBEDDING_DEPLOYMENT",
        "AZURE_EMBEDDING_DIMENSIONS",
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_INDEX_NAME",
    )
    missing = [
        name
        for name in required_names
        if not os.getenv(name) or str(os.getenv(name)).startswith("<")
    ]
    if missing:
        raise RuntimeError("Missing local configuration: " + ", ".join(missing))

    try:
        dimensions = int(os.environ["AZURE_EMBEDDING_DIMENSIONS"])
    except ValueError as error:
        raise RuntimeError("AZURE_EMBEDDING_DIMENSIONS must be an integer") from error
    if dimensions <= 0:
        raise RuntimeError("AZURE_EMBEDDING_DIMENSIONS must be positive")

    return RetrievalConfig(
        tenant_id=os.environ["AZURE_TENANT_ID"],
        openai_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/"),
        embedding_deployment=os.environ["AZURE_EMBEDDING_DEPLOYMENT"],
        embedding_dimensions=dimensions,
        search_endpoint=os.environ["AZURE_SEARCH_ENDPOINT"].rstrip("/"),
        search_index_name=os.environ["AZURE_SEARCH_INDEX_NAME"],
    )


def openai_base_url(endpoint: str) -> str:
    if endpoint.endswith("/openai/v1"):
        return f"{endpoint}/"
    return f"{endpoint}/openai/v1/"


def validated_query(value: str) -> str:
    query = value.strip()
    if not query:
        raise ValueError("query must not be empty")
    if len(query) > MAX_QUERY_CHARACTERS:
        raise ValueError(
            f"query must contain at most {MAX_QUERY_CHARACTERS} characters"
        )
    return query


def validate_limits(top: int, vector_candidates: int) -> None:
    if not 1 <= top <= MAX_RESULTS:
        raise ValueError(f"top must be between 1 and {MAX_RESULTS}")
    if not top <= vector_candidates <= MAX_VECTOR_CANDIDATES:
        raise ValueError(
            "vector-candidates must be at least top and no greater than "
            f"{MAX_VECTOR_CANDIDATES}"
        )


def validated_vector(values: object, expected_dimensions: int) -> list[float]:
    if not isinstance(values, (list, tuple)) or len(values) != expected_dimensions:
        raise RuntimeError(
            f"Query embedding must contain exactly {expected_dimensions} values"
        )

    vector: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RuntimeError("Query embedding values must be numeric")
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise RuntimeError("Query embedding values must be finite")
        vector.append(numeric_value)
    return vector


def embed_query(
    client: OpenAI,
    query: str,
    deployment: str,
    dimensions: int,
) -> list[float]:
    response = client.embeddings.create(
        model=deployment,
        input=[query],
        dimensions=dimensions,
    )
    if len(response.data) != 1:
        raise RuntimeError("Embedding response must contain exactly one vector")
    return validated_vector(response.data[0].embedding, dimensions)


def escape_odata_string(value: str) -> str:
    return value.replace("'", "''")


def hybrid_search(
    client: SearchClient,
    query: str,
    query_vector: list[float],
    *,
    top: int = DEFAULT_TOP,
    vector_candidates: int = DEFAULT_VECTOR_CANDIDATES,
    document_id: str | None = None,
) -> list[dict[str, Any]]:
    """Run one Azure-native hybrid query and return prompt-safe evidence."""
    validate_limits(top, vector_candidates)
    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=vector_candidates,
        fields="content_vector",
        exhaustive=False,
    )
    document_filter = None
    if document_id:
        document_filter = f"document_id eq '{escape_odata_string(document_id)}'"

    response = client.search(
        search_text=query,
        search_fields=SEARCH_FIELDS,
        vector_queries=[vector_query],
        select=SELECT_FIELDS,
        filter=document_filter,
        top=top,
    )

    results: list[dict[str, Any]] = []
    for rank, item in enumerate(response, start=1):
        result = {field: item.get(field) for field in SELECT_FIELDS}
        result["rank"] = rank
        result["score"] = item.get("@search.score")
        results.append(result)
    return results


def run_retrieval(
    config: RetrievalConfig,
    query: str,
    *,
    top: int,
    vector_candidates: int,
    document_id: str | None,
) -> list[dict[str, Any]]:
    credential = build_user_credential(config.tenant_id)
    token_provider = get_bearer_token_provider(credential, OPENAI_SCOPE)
    embedding_client = OpenAI(
        base_url=openai_base_url(config.openai_endpoint),
        api_key=token_provider,
        max_retries=8,
    )
    search_client = SearchClient(
        endpoint=config.search_endpoint,
        index_name=config.search_index_name,
        credential=credential,
    )
    try:
        query_vector = embed_query(
            embedding_client,
            query,
            config.embedding_deployment,
            config.embedding_dimensions,
        )
        return hybrid_search(
            search_client,
            query,
            query_vector,
            top=top,
            vector_candidates=vector_candidates,
            document_id=document_id,
        )
    finally:
        search_client.close()
        embedding_client.close()
        credential.close()


def print_results(query: str, results: list[dict[str, Any]]) -> None:
    print(f"Query: {query}")
    print(f"Results: {len(results)}")
    for result in results:
        text = " ".join(str(result.get("text") or "").split())
        snippet = textwrap.shorten(text, width=500, placeholder="...")
        score = result.get("score")
        score_text = f"{score:.6f}" if isinstance(score, (int, float)) else "n/a"
        print()
        print(
            f"#{result['rank']} | score={score_text} | "
            f"page={result.get('page_number')}"
        )
        print(f"Title: {result.get('source_title')}")
        print(f"Source: {result.get('source_reference')}")
        print(f"Chunk: {result.get('chunk_id')}")
        print(f"Evidence: {snippet}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run BM25 + vector hybrid retrieval in Azure AI Search."
    )
    parser.add_argument("--query", required=True, help="Natural-language question.")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP)
    parser.add_argument(
        "--vector-candidates",
        type=int,
        default=DEFAULT_VECTOR_CANDIDATES,
        help="Nearest vector candidates supplied to hybrid rank fusion.",
    )
    parser.add_argument(
        "--document-id",
        help="Optional exact document_id filter.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and parameters without contacting Azure.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    query = validated_query(args.query)
    validate_limits(args.top, args.vector_candidates)
    config = load_config()

    if args.dry_run:
        print("Hybrid retrieval dry run passed")
        print(f"Index: {config.search_index_name}")
        print(f"Embedding deployment: {config.embedding_deployment}")
        print(f"Embedding dimensions: {config.embedding_dimensions}")
        print(f"Top results: {args.top}")
        print(f"Vector candidates: {args.vector_candidates}")
        print("Azure authentication and retrieval: not performed")
        return

    results = run_retrieval(
        config,
        query,
        top=args.top,
        vector_candidates=args.vector_candidates,
        document_id=args.document_id,
    )
    print_results(query, results)


if __name__ == "__main__":
    main()
