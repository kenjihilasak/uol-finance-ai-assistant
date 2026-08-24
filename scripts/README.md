# Pipeline scripts

Scripts are grouped by pipeline stage so the execution order and boundaries are
visible while learning the project.

```text
scripts/
├── stage_00_environment/  # Verify Azure access and required containers
├── stage_01_ingestion/    # Register, validate, and upload source PDFs
├── stage_02_processing/   # Extract page text and create chunks
├── stage_03_embeddings/   # Validate chunks and generate vectors
└── shared/                # Reusable paths, hashes, and validation
```

## Why modules instead of file paths

Run commands from the repository root using Python's module mode:

```bash
python -m scripts.stage_01_ingestion.register_source_pdf --help
```

The `-m` form treats `scripts` as a package, makes imports deterministic, and
avoids modifying `sys.path` inside individual scripts. Each stage can later gain
its own tests or be promoted into an application service without copying shared
logic.

## Stage order

| Stage | Command modules | Azure call |
| --- | --- | --- |
| 00 — Environment | `check_blob_access` | Yes, read-only |
| 01 — Ingestion | `register_source_pdf`, `upload_source_blob` | Registration: no; upload: yes |
| 02 — Processing | `extract_pdf_text`, `chunk_extracted_text` | No |
| 03 — Embeddings | `generate_embeddings` | Dry run: no; generation: yes |

Future indexing, retrieval, serving, and evaluation stages should receive new
numbered folders only when their implementation begins.
