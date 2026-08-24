# Source metadata schema

`register_source_pdf.py` writes an ignored sidecar beside each local PDF:

```text
data/sources/report.pdf
data/sources/report.metadata.json
```

The schema version is `1.0.0`.

| Field | Type | Rule |
| --- | --- | --- |
| `schema_version` | string | Must be `1.0.0`. |
| `document_id` | string | 3-128 lowercase letters, numbers, or hyphens. |
| `title` | string | Human-readable title. |
| `institution` | string | Publisher, owner, or supplying organisation. |
| `document_date` | string | ISO date in `YYYY-MM-DD` format. |
| `registered_at_utc` | string | Registration timestamp in UTC. |
| `sha256` | string | SHA-256 of the exact local PDF bytes. |
| `content_type` | string | Must be `application/pdf`. |
| `status` | string | `current` or `historical`. |
| `size_bytes` | integer | Exact local file size. |
| `local_filename` | string | Must match the adjacent PDF. |
| `blob_name` | string | Immutable, deterministic Azure blob path. |
| `source_reference` | string | Human-readable origin or custodian. |
| `source_url` | string or null | Optional provenance only. |
| `usage_basis` | string | Operator-recorded reason for processing. |
| `rights_note` | string or null | Optional usage, retention, or redistribution restriction. |

If no document ID is supplied, registration builds one from a slug of the
title and the first 12 characters of the source hash. A changed PDF therefore
receives a different default ID and blob path. An identical hash found in
another sidecar is rejected as a duplicate.

The upload and extraction stages reload this sidecar and recalculate the file
size and SHA-256. Extraction copies its provenance fields into the processed
document contract; later chunks carry only the subset needed for retrieval and
citations.
