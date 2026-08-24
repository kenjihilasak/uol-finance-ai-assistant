# Source metadata schema

Registration writes an ignored sidecar beside each PDF:

```text
data/sources/report.pdf
data/sources/report.metadata.json
```

Schema version: `1.0.0`.

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

Without `--document-id`, registration combines a title slug with the first 12
hash characters. Changed content gets a new ID; duplicate content is rejected.

Upload and extraction recalculate size and SHA-256. Extraction carries the
provenance fields forward; chunks keep the subset needed for retrieval.
