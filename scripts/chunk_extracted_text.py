from __future__ import annotations

import argparse
import json
from pathlib import Path

from document_utils import processed_path, sha256_file, sha256_text


SCHEMA_VERSION = "1.0.0"
CHUNKING_METHOD = "page_bounded_character_window"
DEFAULT_MAX_CHARS = 1800
DEFAULT_OVERLAP_CHARS = 200

REQUIRED_SOURCE_FIELDS = {
    "title",
    "institution",
    "source_reference",
    "source_url",
    "document_date",
    "status",
    "sha256",
}


def split_page_text(
    text: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> list[tuple[int, int, str]]:
    """Return deterministic, word-bounded windows from one PDF page."""
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError(
            "overlap_chars must be non-negative and smaller than max_chars"
        )
    if not text:
        return []

    windows: list[tuple[int, int, str]] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + max_chars, text_length)
        if end < text_length:
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary

        candidate = text[start:end]
        chunk_text = candidate.strip()
        if chunk_text:
            leading_whitespace = len(candidate) - len(candidate.lstrip())
            chunk_start = start + leading_whitespace
            chunk_end = chunk_start + len(chunk_text)
            windows.append((chunk_start, chunk_end, chunk_text))

        if end == text_length:
            break
        start = max(end - overlap_chars, start + 1)

    return windows


def load_processed_document(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(f"Processed JSON not found: {path}")

    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise RuntimeError("Processed JSON must be an object")

    if not isinstance(document.get("document_id"), str):
        raise RuntimeError("Processed JSON is missing document_id")

    source = document.get("source")
    if not isinstance(source, dict):
        raise RuntimeError("Processed JSON is missing source")
    missing_source_fields = REQUIRED_SOURCE_FIELDS - source.keys()
    if missing_source_fields:
        raise RuntimeError(
            "Missing source fields: " + ", ".join(sorted(missing_source_fields))
        )

    pages = document.get("pages")
    if not isinstance(pages, list) or not pages:
        raise RuntimeError("Processed JSON must contain a non-empty pages list")

    return document


def build_chunks(
    document: dict[str, object],
    max_chars: int,
    overlap_chars: int,
) -> list[dict[str, object]]:
    document_id = document["document_id"]
    source = document["source"]
    pages = document["pages"]
    if not isinstance(document_id, str) or not isinstance(source, dict):
        raise RuntimeError("Invalid processed document")
    if not isinstance(pages, list):
        raise RuntimeError("Invalid extracted pages")

    chunks: list[dict[str, object]] = []
    for page in pages:
        if not isinstance(page, dict):
            raise RuntimeError("Invalid extracted page")
        page_number = page.get("page_number")
        page_text = page.get("text")
        if not isinstance(page_number, int) or not isinstance(page_text, str):
            raise RuntimeError("A page has an invalid page_number or text")

        windows = split_page_text(page_text, max_chars, overlap_chars)
        for ordinal, (start, end, text) in enumerate(windows, start=1):
            chunks.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "document_id": document_id,
                    "chunk_id": f"{document_id}-p{page_number:04d}-c{ordinal:03d}",
                    "page_number": page_number,
                    "page_range": {"start": page_number, "end": page_number},
                    "character_range": {"start": start, "end": end},
                    "text": text,
                    "source_title": source["title"],
                    "institution": source["institution"],
                    "source_reference": source["source_reference"],
                    "source_url": source["source_url"],
                    "document_date": source["document_date"],
                    "status": source["status"],
                    "source_sha256": source["sha256"],
                    "text_sha256": sha256_text(text),
                }
            )

    if not chunks:
        raise RuntimeError("No text chunks were produced")
    return chunks


def write_chunks(
    chunks: list[dict[str, object]],
    document_id: str,
    source_processed_sha256: str,
    max_chars: int,
    overlap_chars: int,
    output_path: Path,
    overwrite: bool,
) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "document_id": document_id,
        "source_processed_sha256": source_processed_sha256,
        "chunking": {
            "method": CHUNKING_METHOD,
            "max_chars": max_chars,
            "overlap_chars": overlap_chars,
            "cross_page_chunks": False,
        },
        "chunks": chunks,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialised = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    mode = "w" if overwrite else "x"
    try:
        with output_path.open(mode, encoding="utf-8", newline="\n") as output:
            output.write(serialised)
    except FileExistsError as error:
        raise RuntimeError(
            f"Chunk file already exists and will not be overwritten: {output_path}"
        ) from error
    return sha256_text(serialised)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create deterministic, page-bounded chunks from processed JSON."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to a <document-id>.processed.json file.",
    )
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--overlap-chars", type=int, default=DEFAULT_OVERLAP_CHARS)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Explicitly overwrite the generated chunks JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    document = load_processed_document(args.input)
    document_id = str(document["document_id"])
    output_path = processed_path(document_id, "chunks")
    chunks = build_chunks(document, args.max_chars, args.overlap_chars)
    output_sha256 = write_chunks(
        chunks,
        document_id,
        sha256_file(args.input),
        args.max_chars,
        args.overlap_chars,
        output_path,
        args.overwrite,
    )

    print("Local chunking completed")
    print(f"Chunks: {len(chunks)}")
    print(f"Output: {output_path}")
    print(f"Output SHA-256: {output_sha256}")


if __name__ == "__main__":
    main()
