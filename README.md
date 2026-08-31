# UoL Finance AI Assistant

An Azure RAG portfolio project for grounded question answering over approved
financial PDFs. It focuses on provenance, deterministic processing, Entra ID,
citations, and measurable retrieval quality.

## Status

| State | Capabilities |
| --- | --- |
| Implemented | PDF ingestion, extraction, chunking, embeddings, indexing, and hybrid retrieval |
| Provisioned | Chat deployment and three Blob containers |
| Planned | Cited answer generation, RAG API, evaluation runner, telemetry, and UI |

## Start here

PDFs enter through the ignored `data/sources/` directory; the application does
not download them from URLs.

- [Documentation learning path](./docs/README.md)
- [Project architecture](./docs/overview/project-architecture.md)
- [Source ingestion guide](./docs/stage_01_ingestion/source-ingestion.md)
- [Script stages](./scripts/README.md)

## Security

Copy `.env.example` to the ignored `.env` file. Local Azure access uses
`InteractiveBrowserCredential`; deployed services should use managed identity.
Never commit credentials, source PDFs, extracted text, chunks, or embeddings.

## Tests

```bash
python -m unittest discover -s tests -v
```
