from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "university-of-leeds-annual-report-2024-25.processed.json"
)
OUTPUT_PATH = INPUT_PATH.with_name(
    "university-of-leeds-annual-report-2024-25.chunks.json"
)

SCHEMA_VERSION = "1.0.0"
CHUNKING_METHOD = "page_bounded_character_window"
MAX_CHARS = 1800
OVERLAP_CHARS = 200

REQUIRED_SOURCE_FIELDS = {
    "title",
    "source_page_url",
    "document_date",
    "status",
    "sha256",
}


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def split_page_text(text: str) -> list[tuple[int, int, str]]:
    """Return deterministic, word-bounded windows from one PDF page."""
    if not text:
        return []

    windows: list[tuple[int, int, str]] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + MAX_CHARS, text_length)
        if end < text_length:
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary

        chunk_text = text[start:end].strip()
        if chunk_text:
            leading_whitespace = len(text[start:end]) - len(text[start:end].lstrip())
            chunk_start = start + leading_whitespace
            chunk_end = chunk_start + len(chunk_text)
            windows.append((chunk_start, chunk_end, chunk_text))

        if end == text_length:
            break

        start = max(end - OVERLAP_CHARS, start + 1)

    return windows


def load_processed_document(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(f"No se encontro el JSON extraido: {path}")

    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise RuntimeError("El JSON extraido no es un objeto")

    if not isinstance(document.get("document_id"), str):
        raise RuntimeError("Falta document_id en el JSON extraido")

    source = document.get("source")
    if not isinstance(source, dict):
        raise RuntimeError("Falta source en el JSON extraido")
    missing_source_fields = REQUIRED_SOURCE_FIELDS - source.keys()
    if missing_source_fields:
        missing = ", ".join(sorted(missing_source_fields))
        raise RuntimeError(f"Faltan campos de fuente: {missing}")

    pages = document.get("pages")
    if not isinstance(pages, list) or not pages:
        raise RuntimeError("Falta una lista no vacia de paginas")

    return document


def build_chunks(document: dict[str, object]) -> list[dict[str, object]]:
    document_id = document["document_id"]
    source = document["source"]
    pages = document["pages"]
    if not isinstance(document_id, str) or not isinstance(source, dict):
        raise RuntimeError("Documento extraido invalido")
    if not isinstance(pages, list):
        raise RuntimeError("Paginas extraidas invalidas")

    chunks: list[dict[str, object]] = []
    for page in pages:
        if not isinstance(page, dict):
            raise RuntimeError("Pagina extraida invalida")
        page_number = page.get("page_number")
        page_text = page.get("text")
        if not isinstance(page_number, int) or not isinstance(page_text, str):
            raise RuntimeError("Una pagina no tiene page_number o text validos")

        for ordinal, (start, end, text) in enumerate(split_page_text(page_text), start=1):
            chunks.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "document_id": document_id,
                    "chunk_id": f"{document_id}-p{page_number:03d}-c{ordinal:03d}",
                    "page_number": page_number,
                    "page_range": {"start": page_number, "end": page_number},
                    "character_range": {"start": start, "end": end},
                    "text": text,
                    "source_title": source["title"],
                    "source_url": source["source_page_url"],
                    "document_date": source["document_date"],
                    "status": source["status"],
                    "source_sha256": source["sha256"],
                    "text_sha256": sha256_text(text),
                }
            )

    return chunks


def write_chunks(chunks: list[dict[str, object]], overwrite: bool) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "chunking": {
            "method": CHUNKING_METHOD,
            "max_chars": MAX_CHARS,
            "overlap_chars": OVERLAP_CHARS,
            "cross_page_chunks": False,
        },
        "chunks": chunks,
    }
    serialised = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    mode = "w" if overwrite else "x"
    try:
        with OUTPUT_PATH.open(mode, encoding="utf-8", newline="\n") as output:
            output.write(serialised)
    except FileExistsError as error:
        raise RuntimeError(
            f"El archivo de chunks ya existe y no se sobrescribira: {OUTPUT_PATH}"
        ) from error
    return sha256_text(serialised)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crea chunks deterministas y acotados por pagina."
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescribe explicitamente el JSON local de chunks.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    document = load_processed_document(INPUT_PATH)
    chunks = build_chunks(document)
    output_sha256 = write_chunks(chunks, args.overwrite)

    print("Chunking local completado")
    print(f"Chunks: {len(chunks)}")
    print(f"JSON: {OUTPUT_PATH}")
    print(f"SHA-256 JSON: {output_sha256}")
    print("Embeddings, indice y cargas a Azure: no realizados")


if __name__ == "__main__":
    main()
