# RAG approach

## Decision

Use a custom classic RAG pipeline so provenance, retrieval quality, and failure
modes remain visible. The corpus contains only PDFs placed in `data/sources/`
and registered by an operator; URL downloading is not part of the application.

This matches a common enterprise boundary: an approved upstream process
supplies documents, and the AI pipeline validates and processes them.

## Pipeline

1. Register, validate, and hash the PDF.
2. Store an immutable copy in Azure Blob Storage.
3. Extract page-level text and apply quality checks.
4. Create deterministic, page-bounded chunks.
5. Generate embeddings with Microsoft Foundry.
6. Index chunks and vectors in Azure AI Search.
7. Retrieve evidence and return a cited answer or abstain.

Steps 1–5 are implemented. Search indexing is next.

## Direct PDF intake

Direct intake keeps web acquisition concerns outside the RAG pipeline while
preserving SHA-256 deduplication, versioning, and overwrite protection. A future
web, SharePoint, or API connector can feed the same registration boundary.

Public access is not treated as an open licence. PDFs and generated artifacts
stay outside Git, and source metadata records provenance and usage notes.

## Design references

The design follows the classic flow demonstrated by
`Azure-Samples/azure-search-classic-rag` and the vector-index patterns in
`Azure-Samples/azure-search-python-samples`. A full application template is
deferred until retrieval quality is measurable.

## Azure boundary

`FOUNDRY_PROJECT_ENDPOINT` identifies the project.
`AZURE_OPENAI_ENDPOINT` serves model requests. Local access uses Entra ID, not
API keys, connection strings, or SAS tokens.
