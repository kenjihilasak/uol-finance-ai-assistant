# Processed document schema

This document defines the first local representation produced from a verified
source PDF. It is intentionally page-based. Chunking, embeddings, and Azure AI
Search fields are separate later stages.

## Purpose

The processed JSON must make every extracted page traceable to the exact source
PDF. It keeps provenance and extraction details next to the text so that later
retrieval results can cite a page and be reproduced.

## Top-level fields

| Field | Type | Purpose |
| --- | --- | --- |
| `schema_version` | string | Version of this contract. |
| `document_id` | string | Stable, URL-safe identifier derived from the document and source hash. |
| `source` | object | Original document metadata and source blob name. |
| `processing` | object | Extractor, timestamp, mode, and extraction statistics. |
| `pages` | array | Ordered page-level text records. |

## Source object

The `source` object preserves:

- title;
- source landing page and original/resolved PDF URLs;
- document date and download timestamp;
- source PDF SHA-256 and byte size;
- content type and `current` or `historical` status;
- local source filename and immutable source blob name.

The source SHA-256 must match the local PDF before extraction starts.

## Processing object

The `processing` object records:

- processing timestamp in UTC;
- extractor name and installed version;
- extraction mode and relevant options;
- total pages, pages with and without text;
- total character and approximate word counts;
- ratio of pages containing extractable text.

The first implementation uses `pypdf` layout mode. This mode preserves useful
horizontal positioning, but it does not reconstruct the semantic structure of
financial tables.

Visual sampling confirmed a font-mapping artefact in this PDF: the rendered
pound sign (`U+00A3`) is extracted as `U+0141`. The normalisation stage replaces
only that verified mapping and records the rule in `processing.normalisations`.
No other character substitution is applied.

## Page object

Each entry in `pages` contains:

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
  "document_id": "uol-leeds-annual-report-2024-25-e387d079c84a72a4",
  "source": {
    "title": "University of Leeds Annual Report and Financial Statements 2024-25",
    "sha256": "e387d079c84a72a40dcabf04e044dc13b3d043a8845bf348b9a735af8dd98ccd"
  },
  "processing": {
    "extractor": { "name": "pypdf", "version": "6.16.1" },
    "page_count": 160
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
