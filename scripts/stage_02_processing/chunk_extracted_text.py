from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

from scripts.shared.document_utils import processed_path, sha256_file, sha256_text


SCHEMA_VERSION = "2.0.0"
CHUNKING_METHOD = "page_bounded_recursive_text_units"
DEFAULT_TARGET_CHARS = 1200
DEFAULT_MAX_CHARS = 1800
DEFAULT_MIN_CHARS = 300
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


@dataclass(frozen=True)
class TextUnit:
    start: int
    end: int


def trim_span(text: str, start: int, end: int) -> tuple[int, int] | None:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return (start, end) if start < end else None


def paragraph_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    for separator in re.finditer(r"\n[ \t]*\n+", text):
        span = trim_span(text, start, separator.start())
        if span:
            spans.append(span)
        start = separator.end()

    span = trim_span(text, start, len(text))
    if span:
        spans.append(span)
    return spans


def sentence_spans(text: str, start: int, end: int) -> list[tuple[int, int]]:
    paragraph = text[start:end]
    spans: list[tuple[int, int]] = []
    sentence_start = 0
    boundary_pattern = re.compile(r'[.!?](?:["\u2019\u201d)]*)\s+(?=[A-Z0-9\u00a3])')

    for boundary in boundary_pattern.finditer(paragraph):
        punctuation_end = boundary.start() + len(boundary.group(0).rstrip())
        span = trim_span(
            text,
            start + sentence_start,
            start + punctuation_end,
        )
        if span:
            spans.append(span)
        sentence_start = boundary.end()

    span = trim_span(text, start + sentence_start, end)
    if span:
        spans.append(span)
    return spans


def word_bounded_spans(
    text: str, start: int, end: int, max_chars: int
) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    cursor = start

    while cursor < end:
        candidate_end = min(cursor + max_chars, end)
        if candidate_end < end:
            boundary = text.rfind(" ", cursor, candidate_end)
            if boundary > cursor:
                candidate_end = boundary

        span = trim_span(text, cursor, candidate_end)
        if span:
            spans.append(span)
        cursor = max(candidate_end, cursor + 1)

    return spans


def text_units(text: str, max_chars: int) -> list[TextUnit]:
    units: list[TextUnit] = []
    for paragraph_start, paragraph_end in paragraph_spans(text):
        for sentence_start, sentence_end in sentence_spans(
            text, paragraph_start, paragraph_end
        ):
            spans = (
                [(sentence_start, sentence_end)]
                if sentence_end - sentence_start <= max_chars
                else word_bounded_spans(
                    text,
                    sentence_start,
                    sentence_end,
                    max_chars,
                )
            )
            units.extend(TextUnit(start, end) for start, end in spans)
    return units


def rebalance_short_windows(
    text: str,
    windows: list[tuple[int, int, str]],
    min_chars: int,
    max_chars: int,
) -> list[tuple[int, int, str]]:
    """Merge short edge windows when the result remains within max_chars."""
    pending = list(windows)
    balanced: list[tuple[int, int, str]] = []
    index = 0

    while index < len(pending):
        start, end, value = pending[index]
        if len(value) >= min_chars or len(pending) == 1:
            balanced.append((start, end, value))
            index += 1
            continue

        if balanced and end - balanced[-1][0] <= max_chars:
            previous_start = balanced[-1][0]
            balanced[-1] = (
                previous_start,
                end,
                text[previous_start:end],
            )
            index += 1
            continue

        if index + 1 < len(pending):
            next_start, next_end, _ = pending[index + 1]
            if next_end - start <= max_chars:
                pending[index + 1] = (start, next_end, text[start:next_end])
                index += 1
                continue

        balanced.append((start, end, value))
        index += 1

    return balanced


def split_page_text(
    text: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
    target_chars: int | None = None,
    min_chars: int | None = None,
) -> list[tuple[int, int, str]]:
    """Return page-bounded windows using paragraph and sentence boundaries."""
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError(
            "overlap_chars must be non-negative and smaller than max_chars"
        )
    if target_chars is None:
        target_chars = min(DEFAULT_TARGET_CHARS, max_chars)
    if target_chars <= 0 or target_chars > max_chars:
        raise ValueError("target_chars must be positive and no larger than max_chars")
    if min_chars is None:
        min_chars = min(DEFAULT_MIN_CHARS, target_chars)
    if min_chars <= 0 or min_chars > target_chars:
        raise ValueError("min_chars must be positive and no larger than target_chars")
    if not text:
        return []

    units = text_units(text, max_chars)
    if not units:
        return []

    windows: list[tuple[int, int, str]] = []
    first_unit = 0

    while first_unit < len(units):
        last_unit = first_unit
        while last_unit + 1 < len(units):
            current_length = units[last_unit].end - units[first_unit].start
            candidate_length = units[last_unit + 1].end - units[first_unit].start
            if current_length >= target_chars or candidate_length > max_chars:
                break
            last_unit += 1

        chunk_start = units[first_unit].start
        chunk_end = units[last_unit].end
        windows.append((chunk_start, chunk_end, text[chunk_start:chunk_end]))

        if last_unit == len(units) - 1:
            break

        next_unit = last_unit + 1
        overlap_start = last_unit
        while overlap_start >= first_unit:
            overlap_length = units[last_unit].end - units[overlap_start].start
            if overlap_length > overlap_chars:
                break
            next_unit = overlap_start
            overlap_start -= 1

        first_unit = max(first_unit + 1, next_unit)

    return rebalance_short_windows(text, windows, min_chars, max_chars)


def embedding_text(
    source: dict[str, object], page_number: int, text: str
) -> str:
    return (
        f"Document: {source['title']}\n"
        f"Institution: {source['institution']}\n"
        f"Page: {page_number}\n\n{text}"
    )


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
    target_chars: int | None = None,
    min_chars: int | None = None,
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

        windows = split_page_text(
            page_text,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
            target_chars=target_chars,
            min_chars=min_chars,
        )
        for ordinal, (start, end, text) in enumerate(windows, start=1):
            vector_text = embedding_text(source, page_number, text)
            chunks.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "document_id": document_id,
                    "chunk_id": f"{document_id}-p{page_number:04d}-c{ordinal:03d}",
                    "page_number": page_number,
                    "page_range": {"start": page_number, "end": page_number},
                    "character_range": {"start": start, "end": end},
                    "text": text,
                    "embedding_text": vector_text,
                    "source_title": source["title"],
                    "institution": source["institution"],
                    "source_reference": source["source_reference"],
                    "source_url": source["source_url"],
                    "document_date": source["document_date"],
                    "status": source["status"],
                    "source_sha256": source["sha256"],
                    "text_sha256": sha256_text(text),
                    "embedding_text_sha256": sha256_text(vector_text),
                }
            )

    if not chunks:
        raise RuntimeError("No text chunks were produced")
    return chunks


def write_chunks(
    chunks: list[dict[str, object]],
    document_id: str,
    source_processed_sha256: str,
    target_chars: int,
    min_chars: int,
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
            "split_priority": ["page", "paragraph", "sentence", "word"],
            "target_chars": target_chars,
            "min_chars": min_chars,
            "max_chars": max_chars,
            "overlap_chars": overlap_chars,
            "cross_page_chunks": False,
            "embedding_context": ["document_title", "institution", "page"],
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
    parser.add_argument("--target-chars", type=int, default=DEFAULT_TARGET_CHARS)
    parser.add_argument("--min-chars", type=int, default=DEFAULT_MIN_CHARS)
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
    chunks = build_chunks(
        document,
        args.max_chars,
        args.overlap_chars,
        args.target_chars,
        args.min_chars,
    )
    output_sha256 = write_chunks(
        chunks,
        document_id,
        sha256_file(args.input),
        args.target_chars,
        args.min_chars,
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
