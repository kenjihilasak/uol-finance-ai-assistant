from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

from dotenv import load_dotenv

from scripts.shared.document_utils import (
    PROJECT_ROOT,
    load_and_verify_source,
    resolve_source_pdf,
    slugify,
)


def required_environment() -> tuple[str, str, str]:
    load_dotenv(PROJECT_ROOT / ".env")

    variable_names = (
        "AZURE_STORAGE_ACCOUNT_URL",
        "AZURE_STORAGE_SOURCE_CONTAINER",
        "AZURE_TENANT_ID",
    )
    values: list[str] = []

    for name in variable_names:
        value = os.getenv(name)
        if not value or value.startswith("<"):
            raise RuntimeError(f"Missing required .env variable: {name}")
        values.append(value)

    return values[0], values[1], values[2]


def blob_metadata(metadata: dict[str, object]) -> dict[str, str]:
    """Return a small ASCII-safe metadata set for Azure Blob Storage."""
    return {
        "schema_version": str(metadata["schema_version"]),
        "document_id": str(metadata["document_id"]),
        "institution_slug": slugify(str(metadata["institution"]), 64),
        "document_date": str(metadata["document_date"]),
        "sha256": str(metadata["sha256"]),
        "content_type": str(metadata["content_type"]),
        "status": str(metadata["status"]),
        "size_bytes": str(metadata["size_bytes"]),
    }


def verify_remote_blob(blob_client: object, metadata: dict[str, object]) -> None:
    properties = blob_client.get_blob_properties()
    if properties.size != metadata["size_bytes"]:
        raise RuntimeError("Remote blob size does not match the registered PDF")
    if properties.content_settings.content_type != "application/pdf":
        raise RuntimeError("Remote Content-Type is not application/pdf")
    if properties.metadata.get("sha256") != metadata["sha256"]:
        raise RuntimeError("Remote SHA-256 metadata does not match the PDF")

    remote_digest = hashlib.sha256()
    remote_size = 0
    for block in blob_client.download_blob().chunks():
        remote_digest.update(block)
        remote_size += len(block)

    if remote_size != metadata["size_bytes"]:
        raise RuntimeError("Downloaded remote content has an unexpected size")
    if remote_digest.hexdigest() != metadata["sha256"]:
        raise RuntimeError("Downloaded remote content has a different SHA-256")


def upload_and_verify(pdf_path: Path) -> None:
    from azure.core.exceptions import ResourceExistsError
    from azure.identity import InteractiveBrowserCredential
    from azure.storage.blob import BlobServiceClient, ContentSettings

    metadata = load_and_verify_source(pdf_path)
    account_url, container_name, tenant_id = required_environment()
    blob_name = str(metadata["blob_name"])

    credential = InteractiveBrowserCredential(tenant_id=tenant_id)
    blob_service = BlobServiceClient(account_url=account_url, credential=credential)
    blob_client = blob_service.get_blob_client(
        container=container_name,
        blob=blob_name,
    )

    try:
        print(f"Account: {account_url}")
        print(f"Container: {container_name}")
        print(f"Blob: {blob_name}")
        print("Authenticating with Microsoft Entra ID...")

        uploaded = True
        try:
            with pdf_path.open("rb") as source:
                blob_client.upload_blob(
                    data=source,
                    overwrite=False,
                    metadata=blob_metadata(metadata),
                    content_settings=ContentSettings(content_type="application/pdf"),
                    validate_content=True,
                    max_concurrency=1,
                )
        except ResourceExistsError:
            uploaded = False
            print("Blob already exists; verifying it without overwriting.")

        verify_remote_blob(blob_client, metadata)
        action = "uploaded and verified" if uploaded else "already present and verified"
        print(f"Source blob {action}")
        print(f"Bytes verified: {metadata['size_bytes']}")
        print(f"SHA-256 verified: {metadata['sha256']}")
        print("Overwrite protection: active")
    finally:
        blob_service.close()
        credential.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload a registered local PDF to the source container."
    )
    parser.add_argument(
        "--file",
        required=True,
        help="PDF path inside data/sources, relative to the project root.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pdf_path = resolve_source_pdf(args.file)
    upload_and_verify(pdf_path)


if __name__ == "__main__":
    main()
