# Agent Instructions

## Repository Overview
- Azure RAG portfolio project for grounded question answering over financial PDFs
- Focus on provenance, deterministic processing, Entra ID, citations, and measurable retrieval quality
- Current status: Grounded answer CLI complete; generation evaluation next

## Key Directories
- `data/sources/` - Input PDFs (ignored, not committed)
- `data/processed/` - Extracted text, chunks, and embeddings (ignored, not committed)
- `scripts/` - Pipeline stages organized by number
- `docs/` - Technical documentation following pipeline stages

## Essential Commands
```bash
# Run unit tests
python -m unittest discover -s tests -v

# Process a PDF through all stages
python -m scripts.stage_01_ingestion.register_source_pdf --file data/sources/document.pdf --help
python -m scripts.stage_02_processing.extract_pdf_text --file data/sources/document.pdf
python -m scripts.stage_02_processing.chunk_extracted_text --input data/processed/document.processed.json
python -m scripts.stage_03_embeddings.generate_embeddings --input data/processed/document.chunks.json

# Always run modules from repository root with -m flag
```

## Security Rules
- Never commit credentials, PDFs, extracted text, chunks, or embeddings
- Use Microsoft Entra ID authentication (InteractiveBrowserCredential locally)
- Device Code authentication blocked by tenant Security Defaults
- Copy tracked `.env.example` to ignored `.env` for local configuration

## Development Workflow
1. Place PDF in `data/sources/`
2. Follow stages in numerical order (01 → 02 → 03 → 04)
3. Each stage produces artifacts in `data/processed/`
4. Validate artifacts before proceeding to next stage

## Stage Dependencies
- Stage 01: Register PDF and upload to Blob Storage
- Stage 02: Extract text and create chunks
- Stage 03: Generate embeddings with Foundry
- Stage 04: Index in Azure AI Search
- Stage 05: Retrieval, evaluation, cited generation, and abstention are implemented
- Stage 06: Portfolio UI

## Current Focus
Evaluate groundedness, citation correctness, and abstention before serving.

## Known Deployed Index Difference
- `uol-finance-chunks-v1` contains 490 validated documents and uses 1,536-dimensional HNSW vectors.
- It was initially created with vector profile `default` and `content_vector.retrievable=true`.
- Retrieval queries must explicitly select citation fields and exclude `content_vector`.
- Do not delete or recreate the working index without explicit approval; use a versioned replacement for schema changes.
Schema documented in docs/stage_04_search_index/index-schema.md
