"""Register a locally saved, operator-approved HTML source."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.shared.document_utils import metadata_path_for, resolve_source_document
from scripts.stage_01_ingestion.register_source_pdf import (
    build_metadata,
    write_metadata,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and register HTML already saved in data/sources."
    )
    parser.add_argument("--file", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--institution", required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("--document-date", required=True)
    parser.add_argument("--status", choices=["current", "historical"], required=True)
    parser.add_argument("--source-reference", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--usage-basis", required=True)
    parser.add_argument("--rights-note")
    parser.add_argument("--document-id")
    parser.add_argument("--overwrite-metadata", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_path = resolve_source_document(args.file)
    if source_path.suffix.lower() not in {".html", ".htm"}:
        raise ValueError("The source file must have an .html or .htm extension")
    metadata = build_metadata(args, source_path)
    metadata_path = metadata_path_for(source_path)
    write_metadata(metadata, metadata_path, args.overwrite_metadata)
    print("Local HTML registration completed")
    print(f"HTML: {source_path}")
    print(f"Metadata: {metadata_path}")
    print(f"Document ID: {metadata['document_id']}")
    print(f"SHA-256: {metadata['sha256']}")
    print("Network and Azure operations: not performed")


if __name__ == "__main__":
    main()
