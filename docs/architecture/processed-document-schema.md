# Processed document schema

This document defines the page-level JSON produced from a registered local PDF.
Chunking, embeddings, and Azure AI Search records are later contracts.

## Purpose

The representation makes every extracted page traceable to the exact source
bytes. It retains enough provenance and processing information to reproduce an
artifact and cite a physical PDF page.

## Top-level fields

| Field | Type | Purpose |
| --- | --- | --- |
| `schema_version` | string | Version of this processed-document contract. |
| `document_id` | string | Stable, URL-safe ID copied from source registration. |
| `source` | object | Registered source metadata and immutable blob name. |
| `processing` | object | Extractor settings, timestamp, and quality statistics. |
| `pages` | array | Ordered page-level text records. |

## Source object

| Field | Type | Purpose |
| --- | --- | --- |
| `title` | string | Human-readable document title. |
| `institution` | string | Publisher, owner, or supplying organisation. |
| `document_date` | string | Document date in `YYYY-MM-DD` format. |
| `registered_at_utc` | string | Local registration time in UTC. |
| `sha256` | string | SHA-256 of the source PDF bytes. |
| `content_type` | string | Must be `application/pdf`. |
| `status` | string | `current` or `historical`. |
| `size_bytes` | integer | Source PDF size. |
| `local_filename` | string | Filename under `data/sources/`. |
| `blob_name` | string | Immutable destination name in `source-documents`. |
| `source_reference` | string | Human-readable description of origin or custodian. |
| `source_url` | string or null | Optional provenance URL; never a download instruction. |
| `usage_basis` | string | Operator-recorded reason the document may be processed. |
| `rights_note` | string or null | Copyright, licence, confidentiality, or retention note. |

`usage_basis` and `rights_note` document a human decision; the script cannot
determine copyright or grant permission. The source hash, size, content type,
filename, and document ID must match the registration sidecar before extraction
starts.

## Processing object

The object records:

- processing timestamp in UTC;
- extractor name and installed version;
- extraction mode and relevant options;
- text normalisation rules;
- configured minimum text-page ratio;
- total pages, pages with and without text;
- total character and approximate word counts;
- observed ratio of pages containing extractable text.

The first implementation uses `pypdf` layout mode. It normalises line endings
and trailing whitespace only. It does not perform document-specific character
substitutions or claim to reconstruct the semantic structure of financial
tables. A low text-page ratio stops processing so image-only PDFs can be sent
to a separately designed OCR path.

## Page object

| Field | Type | Purpose |
| --- | --- | --- |
| `page_number` | integer | One-based physical PDF page number. |
| `text` | string | Extracted and minimally normalised page text. |
| `character_count` | integer | Number of characters in `text`. |
| `word_count` | integer | Approximate whitespace-delimited word count. |
| `sha256` | string | SHA-256 of the UTF-8 page text. |

Page hashes detect accidental text changes between extraction and chunking.
They do not replace the source PDF hash.

## Example shape

```json
{
  "schema_version": "1.0.0",
  "document_id": "example-annual-report-2025-a1b2c3d4e5f6",
  "source": {
    "title": "Example Annual Report 2025",
    "institution": "Example Institution",
    "document_date": "2025-07-31",
    "registered_at_utc": "2026-08-24T10:15:00Z",
    "sha256": "source-pdf-sha256",
    "content_type": "application/pdf",
    "status": "current",
    "size_bytes": 123456,
    "local_filename": "example-annual-report-2025.pdf",
    "blob_name": "example-institution/2025/example-annual-report-2025-a1b2c3d4e5f6/example-annual-report-2025.pdf",
    "source_reference": "Provided by the document owner",
    "source_url": null,
    "usage_basis": "Operator-confirmed portfolio analysis",
    "rights_note": "Do not redistribute the source document"
  },
  "processing": {
    "processed_at_utc": "2026-08-24T10:20:00Z",
    "extractor": {"name": "pypdf", "version": "6.16.1"},
    "extraction_mode": "layout",
    "normalisations": [
      "line_endings_to_lf",
      "trailing_whitespace_removed"
    ],
    "minimum_text_page_ratio": 0.8,
    "page_count": 100,
    "pages_with_text": 100,
    "pages_without_text": 0,
    "text_page_ratio": 1.0,
    "total_character_count": 250000,
    "total_word_count": 40000
  },
  "pages": [
    {
      "page_number": 1,
      "text": "Extracted page text...",
      "character_count": 22,
      "word_count": 3,
      "sha256": "page-text-sha256"
    }
  ]
}
```
