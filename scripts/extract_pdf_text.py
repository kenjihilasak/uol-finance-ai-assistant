from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from document_utils import (
    load_and_verify_source,
    processed_path,
    resolve_source_pdf,
)


SCHEMA_VERSION = "1.0.0"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalise_page_text(value: str) -> str:
    normalised = value.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in normalised.splitlines()]
    return "\n".join(lines).strip()


def extract_pages(reader: object) -> list[dict[str, object]]:
    pages: list[dict[str, object]] = []

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            extracted = page.extract_text(
                extraction_mode="layout",
                layout_mode_space_vertically=False,
            )
        except Exception as error:
            raise RuntimeError(f"Could not extract page {page_number}") from error

        text = normalise_page_text(extracted or "")
        pages.append(
            {
                "page_number": page_number,
                "text": text,
                "character_count": len(text),
                "word_count": len(text.split()),
                "sha256": sha256_bytes(text.encode("utf-8")),
            }
        )

    return pages


def build_processed_document(
    metadata: dict[str, object],
    pages: list[dict[str, object]],
    extractor_version: str,
    min_text_page_ratio: float,
) -> dict[str, object]:
    page_count = len(pages)
    if page_count == 0:
        raise RuntimeError("The PDF contains no pages")

    pages_with_text = sum(bool(page["text"]) for page in pages)
    pages_without_text = page_count - pages_with_text
    text_page_ratio = pages_with_text / page_count

    if text_page_ratio < min_text_page_ratio:
        raise RuntimeError(
            f"Only {text_page_ratio:.1%} of pages contain extractable text; "
            "review OCR or the extractor before continuing"
        )

    source_fields = (
        "title",
        "institution",
        "document_date",
        "registered_at_utc",
        "sha256",
        "content_type",
        "status",
        "size_bytes",
        "local_filename",
        "blob_name",
        "source_reference",
        "source_url",
        "usage_basis",
        "rights_note",
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "document_id": metadata["document_id"],
        "source": {field: metadata[field] for field in source_fields},
        "processing": {
            "processed_at_utc": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "extractor": {"name": "pypdf", "version": extractor_version},
            "extraction_mode": "layout",
            "layout_mode_space_vertically": False,
            "normalisations": [
                "line_endings_to_lf",
                "trailing_whitespace_removed",
            ],
            "minimum_text_page_ratio": min_text_page_ratio,
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


def write_json(document: dict[str, object], output_path: Path, overwrite: bool) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialised = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    mode = "w" if overwrite else "x"

    try:
        with output_path.open(mode, encoding="utf-8", newline="\n") as output:
            output.write(serialised)
    except FileExistsError as error:
        raise RuntimeError(
            f"Processed file already exists and will not be overwritten: {output_path}"
        ) from error

    return sha256_bytes(serialised.encode("utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract a registered local PDF to page-level JSON."
    )
    parser.add_argument(
        "--file",
        required=True,
        help="PDF path inside data/sources, relative to the project root.",
    )
    parser.add_argument(
        "--min-text-page-ratio",
        type=float,
        default=0.80,
        help=(
            "Minimum fraction of pages that must contain extractable text "
            "(default: 0.80)."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Explicitly overwrite the generated processed JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not 0 <= args.min_text_page_ratio <= 1:
        raise ValueError("--min-text-page-ratio must be between 0 and 1")

    import pypdf
    from pypdf import PdfReader

    pdf_path = resolve_source_pdf(args.file)
    metadata = load_and_verify_source(pdf_path)
    output_path = processed_path(str(metadata["document_id"]), "processed")

    print(f"Verified PDF: {pdf_path.name}")
    print(f"Source SHA-256: {metadata['sha256']}")
    print(f"Extractor: pypdf {pypdf.__version__} (layout)")

    pages = extract_pages(PdfReader(pdf_path, strict=False))
    document = build_processed_document(
        metadata,
        pages,
        pypdf.__version__,
        args.min_text_page_ratio,
    )
    output_sha256 = write_json(document, output_path, args.overwrite)
    processing = document["processing"]
    if not isinstance(processing, dict):
        raise RuntimeError("Invalid processing summary")

    print("Local extraction completed")
    print(f"Pages: {processing['page_count']}")
    print(f"Pages with text: {processing['pages_with_text']}")
    print(f"Output: {output_path}")
    print(f"Output SHA-256: {output_sha256}")


if __name__ == "__main__":
    main()
