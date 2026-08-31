# Pipeline scripts

```text
scripts/
├── stage_00_environment/  # Verify Azure access
├── stage_01_ingestion/    # Register and upload PDFs
├── stage_02_processing/   # Extract text and create chunks
├── stage_03_embeddings/   # Generate vectors
├── stage_04_search_index/ # Create and populate search index
├── stage_05_retrieval/    # Run BM25 + vector retrieval
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
| 01 | `register_source_pdf`, `upload_source_blob` | Upload only |
| 02 | `extract_pdf_text`, `chunk_extracted_text` | None |
| 03 | `generate_embeddings` | None in dry run; model call otherwise |
| 04 | `create_index`, `upload_documents` | Search index management |
| 05 | Retrieval, positive generation, and abstention evaluation | Search and model calls |

Add future stage folders only when their code is implemented.
