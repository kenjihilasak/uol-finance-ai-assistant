from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv

from scripts.shared.document_utils import PROJECT_ROOT
from scripts.shared.azure_auth import build_user_credential


def required_environment() -> tuple[str, str, set[str]]:
    load_dotenv(PROJECT_ROOT / ".env")
    account_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
    tenant_id = os.getenv("AZURE_TENANT_ID")
    container_variables = (
        "AZURE_STORAGE_SOURCE_CONTAINER",
        "AZURE_STORAGE_PROCESSED_CONTAINER",
        "AZURE_STORAGE_EVALUATION_CONTAINER",
    )

    if not account_url or account_url.startswith("<"):
        raise RuntimeError("Missing AZURE_STORAGE_ACCOUNT_URL in .env")
    if not tenant_id or tenant_id.startswith("<"):
        raise RuntimeError("Missing AZURE_TENANT_ID in .env")

    missing = [name for name in container_variables if not os.getenv(name)]
    if missing:
        raise RuntimeError("Missing .env variables: " + ", ".join(missing))

    expected_containers = {str(os.environ[name]) for name in container_variables}
    return account_url, tenant_id, expected_containers


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify read access to the configured Azure Blob containers."
    )
    return parser.parse_args()


def main() -> None:
    parse_args()

    from azure.storage.blob import BlobServiceClient

    account_url, tenant_id, expected_containers = required_environment()
    credential = build_user_credential(tenant_id)
    blob_service = BlobServiceClient(account_url=account_url, credential=credential)

    try:
        print(f"Connecting to: {account_url}")
        available_containers = {
            container["name"] for container in blob_service.list_containers()
        }

        print("Expected containers:")
        for name in sorted(expected_containers):
            status = "OK" if name in available_containers else "NOT FOUND"
            print(f"- {name}: {status}")
    finally:
        blob_service.close()
        credential.close()


if __name__ == "__main__":
    main()
