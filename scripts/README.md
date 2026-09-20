# Pipeline scripts

```text
scripts/
├── stage_00_environment/  # Verify Azure access
├── stage_01_ingestion/    # Register and upload PDF/HTML sources
├── stage_02_processing/   # Extract pages/sections and create chunks
├── stage_03_embeddings/   # Generate vectors
├── stage_04_search_index/ # Create and populate search index
├── stage_05_retrieval/    # Run BM25 + vector retrieval
├── stage_06_triage/       # Classify, apply safe routing, and evaluate
└── shared/                # Shared validation and hashing
```

Run modules from the repository root:

```bash
python -m scripts.stage_01_ingestion.register_source_pdf --help
```

Using `python -m` keeps package imports deterministic and avoids per-script
`sys.path` changes.

| Stage | Modules | Azure access |
| --- | --- | --- |
| 00 | `check_blob_access` | Read-only |
| 01 | `register_source_pdf`, `register_source_html`, `upload_source_blob` | Upload only |
| 02 | `extract_pdf_text`, `extract_html_text`, `chunk_extracted_text` | None |
| 03 | `generate_embeddings` | None in dry run; model call otherwise |
| 04 | `create_index`, `upload_documents` | Search index management |
| 05 | Retrieval, positive generation, and abstention evaluation | Search and model calls |
| 06 | Classification, deterministic routing, and triage evaluation | Model calls in live mode |

Add future stage folders only when their code is implemented.
