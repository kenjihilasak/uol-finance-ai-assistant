# Portfolio RAG approach

This is a small, explainable RAG portfolio project for financial documents. It
uses a custom pipeline so provenance, retrieval quality, and failure modes stay
visible.

## Scope

The corpus consists only of PDFs that an operator has deliberately placed in
`data/sources/` and registered. The application does not download from URLs.
This models a common enterprise boundary: a document owner, data steward, or
approved upstream process supplies the files; the AI pipeline validates and
processes them.

The initial demonstration can use publicly accessible institutional financial
reports. Public accessibility alone is not treated as an open licence, so raw
PDFs, extracted text, chunks, and embeddings remain outside Git. The source
sidecar records provenance, a human-confirmed usage basis, and an optional
rights note.

## Chosen approach

1. Register and hash each approved local PDF.
2. Store an immutable verified copy in Azure Blob Storage.
3. Extract page-level text with quality checks.
4. Create deterministic, page-bounded chunks with source metadata.
5. Generate embeddings with the Foundry embedding deployment.
6. Upload chunks and vectors to a versioned Azure AI Search index.
7. Retrieve evidence using keyword and vector search, then generate a cited
   answer or abstain.

Steps 1-5 have implementation scripts. Azure AI Search indexing is the next
development milestone.

## Why direct PDF intake

Removing URL acquisition keeps the core system focused and more realistic for
controlled enterprise ingestion:

- provenance is recorded explicitly rather than inferred from a URL;
- local, SharePoint, email, API, or data-platform sources can all feed the same
  boundary later;
- URL redirects, domain allowlists, download timeouts, and web content-type
  behavior do not complicate the RAG pipeline;
- file validation, SHA-256 deduplication, versioning, and overwrite protection
  still apply unchanged.

If automated web acquisition becomes a real requirement, it should be a
separate upstream adapter with its own allowlist, network controls, and tests.

## Azure references used as patterns

- `Azure-Samples/azure-search-classic-rag` informs the classic sequence:
  chunk, embed, index, retrieve, then generate.
- `Azure-Samples/azure-search-python-samples` informs the later vector index
  schema and push-upload code.

The full `azure-search-openai-demo` template is intentionally not adopted yet.
It is a useful UI reference, but would hide learning behind deployment
infrastructure before the retrieval baseline is measurable.

## Endpoint boundary

`FOUNDRY_PROJECT_ENDPOINT` identifies the Foundry project. Embeddings use the
OpenAI-compatible endpoint configured as `AZURE_OPENAI_ENDPOINT`. Local
authentication uses Microsoft Entra ID; no API keys, connection strings, or SAS
tokens are required.
