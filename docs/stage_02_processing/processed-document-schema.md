# Processed document schema

Stage 02 writes page-level JSON to:

```text
data/processed/<document-id>.processed.json
```

Schema version: `1.0.0`.

## Top level

| Field | Type | Purpose |
| --- | --- | --- |
| `schema_version` | string | Contract version |
| `document_id` | string | ID created during registration |
| `source` | object | Verified source metadata |
| `processing` | object | Extraction settings and quality metrics |
| `pages` | array | Ordered page records |

## Source

`source` copies every field from the
[source metadata schema](../stage_01_ingestion/source-metadata-schema.md) except
its `schema_version` and `document_id`; the document ID is already top-level.
Extraction first revalidates the PDF size, content type, filename, and SHA-256.

## Processing

| Field group | Contents |
| --- | --- |
| Execution | `processed_at_utc`, extractor name and version |
| Settings | extraction mode, layout option, normalisations |
| Quality gate | minimum and observed text-page ratios |
| Counts | pages, non-empty pages, characters, and approximate words |

The current extractor uses `pypdf` layout mode and only normalises line endings
and trailing whitespace. It does not reconstruct financial tables. Extraction
stops below the configured text-page ratio so image-only PDFs can be reviewed
for OCR.

## Page

| Field | Type | Purpose |
| --- | --- | --- |
| `page_number` | integer | One-based physical PDF page |
| `text` | string | Minimally normalised text |
| `character_count` | integer | Text length |
| `word_count` | integer | Approximate whitespace-delimited count |
| `sha256` | string | Hash of the UTF-8 page text |

Page hashes detect changes between extraction and chunking; the source PDF hash
remains the document-level integrity check.

## Shape

```json
{
  "schema_version": "1.0.0",
  "document_id": "example-report-a1b2c3d4e5f6",
  "source": {
    "title": "Example Report",
    "sha256": "source-pdf-sha256",
    "source_reference": "Provided by the document owner"
  },
  "processing": {
    "extractor": {"name": "pypdf", "version": "6.16.1"},
    "page_count": 100,
    "text_page_ratio": 1.0
  },
  "pages": [
    {
      "page_number": 1,
      "text": "Extracted text...",
      "character_count": 17,
      "word_count": 2,
      "sha256": "page-text-sha256"
    }
  ]
}
```

The example is abbreviated; the tables and linked source schema define the full
contract.
