"""Create the versioned Azure AI Search hybrid index."""

from __future__ import annotations

import argparse
import os

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    HnswParameters,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchAlgorithmMetric,
    VectorSearchProfile,
)
from dotenv import load_dotenv

from scripts.shared.azure_auth import build_user_credential
from scripts.shared.document_utils import PROJECT_ROOT


VECTOR_ALGORITHM_NAME = "uol-hnsw-config"
VECTOR_PROFILE_NAME = "uol-vector-profile"


def build_search_index(index_name: str, vector_dimensions: int) -> SearchIndex:
    if not index_name:
        raise ValueError("index_name must not be empty")
    if vector_dimensions <= 0:
        raise ValueError("vector_dimensions must be positive")

    fields = [
        SimpleField(
            name="chunk_id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="document_id",
            type=SearchFieldDataType.String,
            filterable=True,
            sortable=True,
        ),
        SearchField(
            name="text",
            type=SearchFieldDataType.String,
            searchable=True,
        ),
        SearchField(
            name="embedding_text",
            type=SearchFieldDataType.String,
            searchable=True,
        ),
        SearchField(
            name="source_title",
            type=SearchFieldDataType.String,
            searchable=True,
            sortable=True,
        ),
        SearchField(
            name="institution",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
            sortable=True,
        ),
        SearchField(
            name="source_reference",
            type=SearchFieldDataType.String,
            searchable=True,
        ),
        SearchField(
            name="source_url",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
        ),
        SearchField(
            name="status",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
            sortable=True,
        ),
        SearchField(
            name="embedding_deployment",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
        ),
        SimpleField(
            name="page_number",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="document_date",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="source_sha256",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="text_sha256",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="embedding_text_sha256",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SearchField(
            name="page_range",
            type=SearchFieldDataType.ComplexType,
            fields=[
                SimpleField(name="start", type=SearchFieldDataType.Int32),
                SimpleField(name="end", type=SearchFieldDataType.Int32),
            ],
        ),
        SearchField(
            name="character_range",
            type=SearchFieldDataType.ComplexType,
            fields=[
                SimpleField(name="start", type=SearchFieldDataType.Int32),
                SimpleField(name="end", type=SearchFieldDataType.Int32),
            ],
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            retrievable=False,
            vector_search_dimensions=vector_dimensions,
            vector_search_profile_name=VECTOR_PROFILE_NAME,
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name=VECTOR_ALGORITHM_NAME,
                parameters=HnswParameters(
                    m=4,
                    ef_construction=400,
                    ef_search=500,
                    metric=VectorSearchAlgorithmMetric.COSINE,
                ),
            )
        ],
        profiles=[
            VectorSearchProfile(
                name=VECTOR_PROFILE_NAME,
                algorithm_configuration_name=VECTOR_ALGORITHM_NAME,
            )
        ],
    )
    return SearchIndex(name=index_name, fields=fields, vector_search=vector_search)


def create_search_index(
    service_endpoint: str,
    index_name: str,
    tenant_id: str,
    vector_dimensions: int,
) -> None:
    credential = build_user_credential(tenant_id)
    index_client = SearchIndexClient(
        endpoint=service_endpoint,
        credential=credential,
    )
    try:
        index_client.create_index(build_search_index(index_name, vector_dimensions))
    finally:
        index_client.close()
        credential.close()
    print(f"Index '{index_name}' created successfully.")


def load_config() -> tuple[str, str, str, int]:
    load_dotenv(PROJECT_ROOT / ".env")
    names = (
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_INDEX_NAME",
        "AZURE_TENANT_ID",
        "AZURE_EMBEDDING_DIMENSIONS",
    )
    missing = [
        name
        for name in names
        if not os.getenv(name) or str(os.getenv(name)).startswith("<")
    ]
    if missing:
        raise RuntimeError("Missing local configuration: " + ", ".join(missing))

    try:
        dimensions = int(os.environ["AZURE_EMBEDDING_DIMENSIONS"])
    except ValueError as error:
        raise RuntimeError("AZURE_EMBEDDING_DIMENSIONS must be an integer") from error

    return (
        os.environ["AZURE_SEARCH_ENDPOINT"].rstrip("/"),
        os.environ["AZURE_SEARCH_INDEX_NAME"],
        os.environ["AZURE_TENANT_ID"],
        dimensions,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create the configured Azure AI Search hybrid index."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and validate the schema without contacting Azure.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    endpoint, index_name, tenant_id, dimensions = load_config()
    index = build_search_index(index_name, dimensions)

    if args.dry_run:
        print("Search index dry run passed")
        print(f"Index: {index.name}")
        print(f"Fields: {len(index.fields)}")
        print(f"Vector dimensions: {dimensions}")
        print("Azure authentication and index creation: not performed")
        return

    create_search_index(endpoint, index_name, tenant_id, dimensions)


if __name__ == "__main__":
    main()
