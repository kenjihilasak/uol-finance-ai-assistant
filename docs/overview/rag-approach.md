# RAG approach

## Decision

Use a custom classic RAG pipeline so ingestion, retrieval, citations and
failure modes remain inspectable and independently testable.

```text
approved source
→ validate and hash
→ extract and chunk
→ embed
→ index text, vectors and provenance
→ category-filtered hybrid retrieval
→ grounded draft with controlled citations
```

## Key choices

- Operator-provided PDF and HTML snapshots; no runtime URL downloading.
- Immutable source copy and deterministic hashes for traceability.
- Page-bounded chunks so citations map back to original sources.
- `text-embedding-3-small` for documents and user enquiries.
- Azure AI Search for BM25 text search, vector similarity and RRF fusion.
- Top-five evidence context with source IDs constrained by JSON Schema.
- Abstention when approved evidence is insufficient.
- RAG starts only after deterministic triage permits generation.

## Evidence

- [Chunking strategy](../stage_02_processing/chunking-strategy.md)
- [Embedding generation](../stage_03_embeddings/embedding-generation.md)
- [Hybrid retrieval](../stage_05_retrieval/hybrid-retrieval.md)
- [Retrieval design decisions](../stage_05_retrieval/retrieval-design-decisions.md)
- [Grounded answer generation](../stage_05_retrieval/grounded-answer-generation.md)
- [Retrieval evaluation](../stage_05_retrieval/retrieval-evaluation.md)
