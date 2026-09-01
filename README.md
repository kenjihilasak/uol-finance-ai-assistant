# UoL Finance AI Assistant

An Azure RAG portfolio project for grounded question answering over approved
financial PDFs. It focuses on provenance, deterministic processing, Entra ID,
citations, and measurable retrieval quality.

## Status

| State | Capabilities |
| --- | --- |
| Implemented | PDF pipeline, evaluated RAG, FastAPI contract, public document catalog, portfolio UI |
| Provisioned | Chat deployment and three Blob containers |
| Planned | Railway deployment, persistent rate limiting, telemetry, authenticated ingestion |

## Start here

PDFs enter through the ignored `data/sources/` directory; the application does
not download them from URLs.

- [Documentation learning path](./docs/README.md)
- [Project architecture](./docs/overview/project-architecture.md)
- [Retrieval baseline](./docs/stage_05_retrieval/retrieval-evaluation.md)
- [Grounded answers](./docs/stage_05_retrieval/grounded-answer-generation.md)
- [Portfolio UI decision](./docs/overview/ui-options.md)
- [Serving and deployment guide](./docs/stage_06_serving/api-and-portfolio.md)
- [Source ingestion guide](./docs/stage_01_ingestion/source-ingestion.md)
- [Script stages](./scripts/README.md)

## Security

Copy `.env.example` to the ignored `.env` file. Local Azure access uses
`InteractiveBrowserCredential`; Railway uses an Entra ID service principal with
least-privilege RBAC. Never commit credentials, source PDFs, extracted text,
chunks, or embeddings.

## Tests

```bash
python -m unittest discover -s tests -v
```
