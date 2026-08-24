from __future__ import annotations

import os

from dotenv import load_dotenv


def required_environment() -> tuple[str, str, set[str]]:
    load_dotenv()
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


def main() -> None:
    from azure.identity import InteractiveBrowserCredential
    from azure.storage.blob import BlobServiceClient

    account_url, tenant_id, expected_containers = required_environment()
    credential = InteractiveBrowserCredential(tenant_id=tenant_id)
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
