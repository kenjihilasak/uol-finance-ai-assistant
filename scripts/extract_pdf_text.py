from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pypdf
from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = (
    PROJECT_ROOT
    / "data"
    / "sources"
    / "university-of-leeds-annual-report-2024-25.pdf"
)
METADATA_PATH = PDF_PATH.with_suffix(".metadata.json")
OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "university-of-leeds-annual-report-2024-25.processed.json"
)

DOCUMENT_ID_PREFIX = "uol-leeds-annual-report-2024-25"
SOURCE_BLOB_NAME = (
    "university-of-leeds/annual-reports/2024-25/"
    "university-of-leeds-annual-report-2024-25.pdf"
)
SCHEMA_VERSION = "1.0.0"
MIN_TEXT_PAGE_RATIO = 0.80

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


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)

    return digest.hexdigest()


def load_and_verify_source() -> dict[str, object]:
    if not PDF_PATH.is_file():
        raise FileNotFoundError(f"No se encontro el PDF local: {PDF_PATH}")

    if not METADATA_PATH.is_file():
        raise FileNotFoundError(
            f"No se encontraron los metadatos locales: {METADATA_PATH}"
        )

    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise RuntimeError("Los metadatos locales no son un objeto JSON")

    missing_fields = REQUIRED_METADATA_FIELDS - metadata.keys()
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise RuntimeError(f"Faltan campos de metadatos: {missing}")

    with PDF_PATH.open("rb") as source:
        if source.read(5) != b"%PDF-":
            raise RuntimeError("El archivo local no tiene una firma PDF valida")

    expected_size = metadata["size_bytes"]
    if not isinstance(expected_size, int):
        raise RuntimeError("size_bytes debe ser un numero entero")

    actual_size = PDF_PATH.stat().st_size
    if actual_size != expected_size:
        raise RuntimeError("El tamano del PDF no coincide con los metadatos")

    expected_sha256 = str(metadata["sha256"]).lower()
    actual_sha256 = sha256_file(PDF_PATH)
    if actual_sha256 != expected_sha256:
        raise RuntimeError("El SHA-256 del PDF no coincide con los metadatos")

    if metadata["content_type"] != "application/pdf":
        raise RuntimeError("El tipo de contenido no es application/pdf")

    return metadata


def normalise_page_text(value: str) -> str:
    normalised = value.replace("\r\n", "\n").replace("\r", "\n")
    normalised = normalised.replace("\u0141", "\u00a3")
    lines = [line.rstrip() for line in normalised.splitlines()]
    return "\n".join(lines).strip()


def extract_pages(reader: PdfReader) -> list[dict[str, object]]:
    pages: list[dict[str, object]] = []

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            extracted = page.extract_text(
                extraction_mode="layout",
                layout_mode_space_vertically=False,
            )
        except Exception as error:
            raise RuntimeError(
                f"No se pudo extraer la pagina {page_number}"
            ) from error

        text = normalise_page_text(extracted or "")
        text_bytes = text.encode("utf-8")

        pages.append(
            {
                "page_number": page_number,
                "text": text,
                "character_count": len(text),
                "word_count": len(text.split()),
                "sha256": sha256_bytes(text_bytes),
            }
        )

    return pages


def build_processed_document(
    metadata: dict[str, object],
    pages: list[dict[str, object]],
) -> dict[str, object]:
    page_count = len(pages)
    if page_count == 0:
        raise RuntimeError("El PDF no contiene paginas")

    pages_with_text = sum(bool(page["text"]) for page in pages)
    pages_without_text = page_count - pages_with_text
    text_page_ratio = pages_with_text / page_count

    if text_page_ratio < MIN_TEXT_PAGE_RATIO:
        raise RuntimeError(
            "Menos del 80% de las paginas contienen texto extraible; "
            "se requiere revisar OCR o el extractor"
        )

    source_sha256 = str(metadata["sha256"]).lower()
    document_id = f"{DOCUMENT_ID_PREFIX}-{source_sha256[:16]}"

    return {
        "schema_version": SCHEMA_VERSION,
        "document_id": document_id,
        "source": {
            "title": metadata["title"],
            "source_page_url": metadata["source_page_url"],
            "original_url": metadata["original_url"],
            "resolved_url": metadata["resolved_url"],
            "document_date": metadata["document_date"],
            "downloaded_at_utc": metadata["downloaded_at_utc"],
            "sha256": source_sha256,
            "content_type": metadata["content_type"],
            "status": metadata["status"],
            "size_bytes": metadata["size_bytes"],
            "local_filename": PDF_PATH.name,
            "blob_name": SOURCE_BLOB_NAME,
        },
        "processing": {
            "processed_at_utc": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "extractor": {
                "name": "pypdf",
                "version": pypdf.__version__,
            },
            "extraction_mode": "layout",
            "layout_mode_space_vertically": False,
            "normalisations": [
                "verified_u0141_to_u00a3_currency_symbol",
            ],
            "page_count": page_count,
            "pages_with_text": pages_with_text,
            "pages_without_text": pages_without_text,
            "text_page_ratio": round(text_page_ratio, 6),
            "total_character_count": sum(
                int(page["character_count"]) for page in pages
            ),
            "total_word_count": sum(int(page["word_count"]) for page in pages),
        },
        "pages": pages,
    }


def write_processed_document(
    document: dict[str, object], overwrite: bool
) -> str:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    serialised = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    mode = "w" if overwrite else "x"

    try:
        with OUTPUT_PATH.open(mode, encoding="utf-8", newline="\n") as output:
            output.write(serialised)
    except FileExistsError as error:
        raise RuntimeError(
            f"El archivo procesado ya existe y no se sobrescribira: {OUTPUT_PATH}"
        ) from error

    return sha256_bytes(serialised.encode("utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extrae un PDF verificado a un JSON por paginas."
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescribe explicitamente el JSON procesado local.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata = load_and_verify_source()

    print(f"PDF verificado: {PDF_PATH.name}")
    print(f"SHA-256 fuente: {metadata['sha256']}")
    print(f"Extractor: pypdf {pypdf.__version__} (layout)")

    reader = PdfReader(PDF_PATH, strict=False)
    pages = extract_pages(reader)
    document = build_processed_document(metadata, pages)
    output_sha256 = write_processed_document(document, args.overwrite)
    processing = document["processing"]

    if not isinstance(processing, dict):
        raise RuntimeError("El resumen de procesamiento no es valido")

    print("Extraccion local completada")
    print(f"Paginas: {processing['page_count']}")
    print(f"Paginas con texto: {processing['pages_with_text']}")
    print(f"Caracteres: {processing['total_character_count']}")
    print(f"Palabras aproximadas: {processing['total_word_count']}")
    print(f"JSON: {OUTPUT_PATH}")
    print(f"SHA-256 JSON: {output_sha256}")
    print("Embeddings e indice: no creados")


if __name__ == "__main__":
    main()
