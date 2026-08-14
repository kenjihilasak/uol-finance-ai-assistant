from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from azure.core.exceptions import ResourceExistsError
from azure.identity import InteractiveBrowserCredential
from azure.storage.blob import BlobServiceClient, ContentSettings
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = (
    PROJECT_ROOT
    / "data"
    / "sources"
    / "university-of-leeds-annual-report-2024-25.pdf"
)
METADATA_PATH = PDF_PATH.with_suffix(".metadata.json")

BLOB_NAME = (
    "university-of-leeds/annual-reports/2024-25/"
    "university-of-leeds-annual-report-2024-25.pdf"
)

REQUIRED_METADATA_FIELDS = {
    "title",
    "source_page_url",
    "original_url",
    "resolved_url",
    "document_date",
    "downloaded_at_utc",
    "sha256",
    "content_type",
    "status",
    "size_bytes",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)

    return digest.hexdigest()


def load_and_verify_local_source() -> dict[str, object]:
    if not PDF_PATH.is_file():
        raise FileNotFoundError(f"No se encontro el PDF local: {PDF_PATH}")

    if not METADATA_PATH.is_file():
        raise FileNotFoundError(
            f"No se encontraron los metadatos locales: {METADATA_PATH}"
        )

    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    missing_fields = REQUIRED_METADATA_FIELDS - metadata.keys()

    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise RuntimeError(f"Faltan campos de metadatos: {missing}")

    with PDF_PATH.open("rb") as source:
        if source.read(5) != b"%PDF-":
            raise RuntimeError("El archivo local no tiene una firma PDF valida")

    actual_size = PDF_PATH.stat().st_size
    if actual_size != metadata["size_bytes"]:
        raise RuntimeError("El tamano local no coincide con los metadatos")

    actual_sha256 = sha256_file(PDF_PATH)
    if actual_sha256 != metadata["sha256"]:
        raise RuntimeError("El SHA-256 local no coincide con los metadatos")

    if metadata["content_type"] != "application/pdf":
        raise RuntimeError("El tipo de contenido local no es application/pdf")

    return metadata


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
            raise RuntimeError(f"Falta una variable requerida en .env: {name}")
        values.append(value)

    return values[0], values[1], values[2]


def blob_metadata(metadata: dict[str, object]) -> dict[str, str]:
    return {
        "institution": "University of Leeds",
        "title": str(metadata["title"]),
        "source_page_url": str(metadata["source_page_url"]),
        "original_url": str(metadata["original_url"]),
        "resolved_url": str(metadata["resolved_url"]),
        "document_date": str(metadata["document_date"]),
        "downloaded_at_utc": str(metadata["downloaded_at_utc"]),
        "sha256": str(metadata["sha256"]),
        "content_type": str(metadata["content_type"]),
        "status": str(metadata["status"]),
        "size_bytes": str(metadata["size_bytes"]),
    }


def upload_and_verify() -> None:
    metadata = load_and_verify_local_source()
    account_url, container_name, tenant_id = required_environment()

    credential = InteractiveBrowserCredential(tenant_id=tenant_id)
    blob_service = BlobServiceClient(
        account_url=account_url,
        credential=credential,
    )
    blob_client = blob_service.get_blob_client(
        container=container_name,
        blob=BLOB_NAME,
    )

    try:
        print(f"Cuenta: {account_url}")
        print(f"Contenedor: {container_name}")
        print(f"Blob: {BLOB_NAME}")
        print("Autenticando con Microsoft Entra ID...")

        try:
            with PDF_PATH.open("rb") as source:
                blob_client.upload_blob(
                    data=source,
                    overwrite=False,
                    metadata=blob_metadata(metadata),
                    content_settings=ContentSettings(
                        content_type="application/pdf"
                    ),
                    validate_content=True,
                    max_concurrency=1,
                )
        except ResourceExistsError as error:
            raise RuntimeError(
                "El blob ya existe y no se sobrescribira"
            ) from error

        properties = blob_client.get_blob_properties()

        if properties.size != metadata["size_bytes"]:
            raise RuntimeError("El tamano remoto no coincide con el local")

        if properties.content_settings.content_type != "application/pdf":
            raise RuntimeError("El Content-Type remoto no es application/pdf")

        if properties.metadata.get("sha256") != metadata["sha256"]:
            raise RuntimeError("El SHA-256 guardado como metadato no coincide")

        remote_digest = hashlib.sha256()
        remote_size = 0

        for chunk in blob_client.download_blob().chunks():
            remote_digest.update(chunk)
            remote_size += len(chunk)

        remote_sha256 = remote_digest.hexdigest()

        if remote_size != metadata["size_bytes"]:
            raise RuntimeError("El contenido remoto tiene un tamano inesperado")

        if remote_sha256 != metadata["sha256"]:
            raise RuntimeError("El contenido remoto tiene un SHA-256 diferente")

        print("Subida y verificacion completadas")
        print(f"Bytes verificados: {remote_size}")
        print(f"SHA-256 verificado: {remote_sha256}")
        print("Content-Type verificado: application/pdf")
        print("Proteccion contra sobrescritura: activa")

    finally:
        blob_service.close()
        credential.close()


if __name__ == "__main__":
    upload_and_verify()
