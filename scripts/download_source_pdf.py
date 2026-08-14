from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


TITLE = "University of Leeds Annual Report and Financial Statements 2024-25"
SOURCE_PAGE_URL = (
    "https://www.leeds.ac.uk/downloads/download/72/corporate_publications"
)
ORIGINAL_URL = (
    "https://www.leeds.ac.uk/download/downloads/id/3533/"
    "annual-report-and-accounts-2024-25.pdf"
)
DOCUMENT_DATE = "2025-07-31"
DOCUMENT_STATUS = "current"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY = PROJECT_ROOT / "data" / "sources"
PDF_PATH = OUTPUT_DIRECTORY / "university-of-leeds-annual-report-2024-25.pdf"
METADATA_PATH = PDF_PATH.with_suffix(".metadata.json")

MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


def require_official_https_url(url: str) -> None:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()

    if parsed.scheme != "https":
        raise ValueError(f"La URL no usa HTTPS: {url}")

    if hostname != "leeds.ac.uk" and not hostname.endswith(".leeds.ac.uk"):
        raise ValueError(f"La URL no pertenece a un dominio oficial de Leeds: {url}")


def download_source() -> dict[str, object]:
    require_official_https_url(SOURCE_PAGE_URL)
    require_official_https_url(ORIGINAL_URL)

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    for path in (PDF_PATH, METADATA_PATH):
        if path.exists():
            raise FileExistsError(
                f"El destino ya existe y no se sobrescribirá: {path}"
            )

    request = Request(
        ORIGINAL_URL,
        headers={"User-Agent": "uol-finance-ai-assistant/0.1"},
    )

    pdf_created = False
    metadata_created = False

    try:
        with urlopen(request, timeout=60) as response:
            if response.status != 200:
                raise RuntimeError(f"Respuesta HTTP inesperada: {response.status}")

            resolved_url = response.geturl()
            require_official_https_url(resolved_url)

            content_type = response.headers.get_content_type()
            if content_type != "application/pdf":
                raise RuntimeError(
                    f"Tipo de contenido inesperado: {content_type}"
                )

            declared_size = response.headers.get("Content-Length")
            if declared_size and int(declared_size) > MAX_DOWNLOAD_BYTES:
                raise RuntimeError("El PDF supera el límite de descarga de 25 MiB")

            sha256 = hashlib.sha256()
            downloaded_bytes = 0
            first_chunk = True

            with PDF_PATH.open("xb") as destination:
                pdf_created = True

                while chunk := response.read(CHUNK_SIZE):
                    if first_chunk:
                        if not chunk.startswith(b"%PDF-"):
                            raise RuntimeError("El archivo no tiene una firma PDF válida")
                        first_chunk = False

                    downloaded_bytes += len(chunk)
                    if downloaded_bytes > MAX_DOWNLOAD_BYTES:
                        raise RuntimeError(
                            "El PDF supera el límite de descarga de 25 MiB"
                        )

                    destination.write(chunk)
                    sha256.update(chunk)

            if downloaded_bytes == 0:
                raise RuntimeError("La descarga produjo un archivo vacío")

        metadata: dict[str, object] = {
            "title": TITLE,
            "source_page_url": SOURCE_PAGE_URL,
            "original_url": ORIGINAL_URL,
            "resolved_url": resolved_url,
            "document_date": DOCUMENT_DATE,
            "downloaded_at_utc": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "sha256": sha256.hexdigest(),
            "content_type": content_type,
            "status": DOCUMENT_STATUS,
            "size_bytes": downloaded_bytes,
        }

        with METADATA_PATH.open("x", encoding="utf-8") as metadata_file:
            metadata_created = True
            json.dump(metadata, metadata_file, indent=2, ensure_ascii=False)
            metadata_file.write("\n")

        return metadata

    except Exception:
        if metadata_created:
            METADATA_PATH.unlink(missing_ok=True)
        if pdf_created:
            PDF_PATH.unlink(missing_ok=True)
        raise


def main() -> None:
    metadata = download_source()

    print(f"PDF descargado: {PDF_PATH}")
    print(f"Metadatos: {METADATA_PATH}")
    print(f"Bytes: {metadata['size_bytes']}")
    print(f"SHA-256: {metadata['sha256']}")
    print(f"Content-Type: {metadata['content_type']}")
    print(f"Estado: {metadata['status']}")


if __name__ == "__main__":
    main()
