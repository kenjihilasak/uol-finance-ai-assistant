from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from document_utils import (
    ALLOWED_DOCUMENT_STATUSES,
    SOURCE_DIRECTORY,
    SOURCE_METADATA_SCHEMA_VERSION,
    metadata_path_for,
    resolve_source_pdf,
    slugify,
    validate_document_id,
    validate_iso_date,
    validate_optional_source_url,
    validate_pdf_file,
)


def find_duplicate_sha256(
    source_directory: Path,
    sha256: str,
    destination_metadata_path: Path,
) -> Path | None:
    for metadata_path in source_directory.rglob("*.metadata.json"):
        if metadata_path.resolve() == destination_metadata_path.resolve():
            continue
        try:
            candidate = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(candidate, dict) and candidate.get("sha256") == sha256:
            return metadata_path
    return None


def build_metadata(args: argparse.Namespace, pdf_path: Path) -> dict[str, object]:
    file_details = validate_pdf_file(pdf_path)
    source_sha256 = str(file_details["sha256"])
    title = args.title.strip()
    institution = args.institution.strip()
    source_reference = args.source_reference.strip()
    usage_basis = args.usage_basis.strip()
    document_date = validate_iso_date(args.document_date)

    required_text = {
        "title": title,
        "institution": institution,
        "source_reference": source_reference,
        "usage_basis": usage_basis,
    }
    empty_fields = [name for name, value in required_text.items() if not value]
    if empty_fields:
        raise ValueError("These fields cannot be empty: " + ", ".join(empty_fields))

    if args.document_id:
        document_id = validate_document_id(args.document_id)
    else:
        document_id = validate_document_id(
            f"{slugify(title, max_length=96)}-{source_sha256[:12]}"
        )

    institution_slug = slugify(institution, max_length=64)
    blob_filename = f"{slugify(pdf_path.stem, max_length=96)}.pdf"
    blob_name = (
        f"{institution_slug}/{document_date[:4]}/"
        f"{document_id}/{blob_filename}"
    )

    return {
        "schema_version": SOURCE_METADATA_SCHEMA_VERSION,
        "document_id": document_id,
        "title": title,
        "institution": institution,
        "document_date": document_date,
        "registered_at_utc": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        **file_details,
        "status": args.status,
        "local_filename": pdf_path.name,
        "blob_name": blob_name,
        "source_reference": source_reference,
        "source_url": validate_optional_source_url(args.source_url),
        "usage_basis": usage_basis,
        "rights_note": args.rights_note.strip() if args.rights_note else None,
    }


def write_metadata(
    metadata: dict[str, object],
    metadata_path: Path,
    overwrite: bool,
) -> None:
    duplicate = find_duplicate_sha256(
        SOURCE_DIRECTORY,
        str(metadata["sha256"]),
        metadata_path,
    )
    if duplicate:
        raise RuntimeError(
            "An identical PDF is already registered by metadata file: "
            f"{duplicate}"
        )

    mode = "w" if overwrite else "x"
    try:
        with metadata_path.open(mode, encoding="utf-8", newline="\n") as output:
            json.dump(metadata, output, ensure_ascii=False, indent=2)
            output.write("\n")
    except FileExistsError as error:
        raise RuntimeError(
            f"Metadata already exists and will not be overwritten: {metadata_path}"
        ) from error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and register a PDF already placed in data/sources. "
            "The command never downloads or copies the source file."
        )
    )
    parser.add_argument(
        "--file",
        required=True,
        help="PDF path inside data/sources, relative to the project root.",
    )
    parser.add_argument("--title", required=True, help="Document title.")
    parser.add_argument("--institution", required=True, help="Document owner.")
    parser.add_argument(
        "--document-date",
        required=True,
        help="Document date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--status",
        choices=sorted(ALLOWED_DOCUMENT_STATUSES),
        required=True,
        help="Whether this source is current or historical.",
    )
    parser.add_argument(
        "--source-reference",
        required=True,
        help="Human-readable origin, such as an official page or internal owner.",
    )
    parser.add_argument(
        "--source-url",
        help="Optional authoritative source URL retained only as provenance.",
    )
    parser.add_argument(
        "--usage-basis",
        required=True,
        help="Operator-confirmed basis for processing this document.",
    )
    parser.add_argument(
        "--rights-note",
        help="Optional copyright, licence, confidentiality, or retention note.",
    )
    parser.add_argument(
        "--document-id",
        help="Optional stable ID; otherwise title and SHA-256 derive it.",
    )
    parser.add_argument(
        "--overwrite-metadata",
        action="store_true",
        help="Explicitly replace only the local metadata sidecar, never the PDF.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pdf_path = resolve_source_pdf(args.file)
    metadata = build_metadata(args, pdf_path)
    metadata_path = metadata_path_for(pdf_path)
    write_metadata(metadata, metadata_path, args.overwrite_metadata)

    print("Local source registration completed")
    print(f"PDF: {pdf_path}")
    print(f"Metadata: {metadata_path}")
    print(f"Document ID: {metadata['document_id']}")
    print(f"Bytes: {metadata['size_bytes']}")
    print(f"SHA-256: {metadata['sha256']}")
    print(f"Blob name: {metadata['blob_name']}")
    print("Network and Azure operations: not performed")


if __name__ == "__main__":
    main()
