"""Add the category field to an existing Azure AI Search index."""

from __future__ import annotations

import argparse

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
)

from scripts.shared.azure_auth import build_user_credential
from scripts.stage_04_search_index.create_index import load_config


def add_category_field(index: SearchIndex) -> bool:
    """Mutate an SDK index object only when the additive field is absent."""
    if any(field.name == "category" for field in index.fields):
        return False
    index.fields.append(
        SimpleField(
            name="category",
            type=SearchFieldDataType.String,
            filterable=True,
            sortable=True,
            facetable=True,
        )
    )
    return True


def update_index(endpoint: str, index_name: str, tenant_id: str) -> None:
    credential = build_user_credential(tenant_id)
    client = SearchIndexClient(endpoint=endpoint, credential=credential)
    try:
        index = client.get_index(index_name)
        if not add_category_field(index):
            print(f"Index '{index_name}' already has category; no change required.")
            return
        client.create_or_update_index(index)
    finally:
        client.close()
        credential.close()
    print(f"Added category to index '{index_name}' without deleting existing data.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add the filterable category field to the configured index."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate local configuration without contacting Azure.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    endpoint, index_name, tenant_id, _ = load_config()
    if args.dry_run:
        print("Category-field migration dry run passed")
        print(f"Index: {index_name}")
        print("Azure authentication and index update: not performed")
        return
    update_index(endpoint, index_name, tenant_id)


if __name__ == "__main__":
    main()
