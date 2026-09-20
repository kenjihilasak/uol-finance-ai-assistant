# Agentic Support Intelligence

An Azure-based staff workbench that categorises unstructured university
enquiries, routes sensitive cases without generation, and drafts cited answers
from an approved knowledge corpus. It focuses on deterministic safety controls,
provenance, Entra ID, human review, and measurable quality.

## Status

| State | Capabilities |
| --- | --- |
| Implemented | PDF/HTML pipeline, evaluated RAG, safe triage, FastAPI, PostgreSQL repository, Excel export, portfolio workbench |
| Provisioned | Chat deployment and three Blob containers |
| Deployment dependent | Railway service, PostgreSQL attachment, secrets, telemetry |

## Start here

Approved PDF and HTML snapshots enter through the ignored `data/sources/`
directory; the application does not download them automatically from URLs.

- [Documentation learning path](./docs/README.md)
- [Project architecture](./docs/overview/project-architecture.md)
- [Retrieval baseline](./docs/stage_05_retrieval/retrieval-evaluation.md)
- [Grounded answers](./docs/stage_05_retrieval/grounded-answer-generation.md)
- [Enquiry triage and safety](./docs/stage_06_triage/enquiry-triage.md)
- [Portfolio UI decision](./docs/overview/ui-options.md)
- [Serving and deployment guide](./docs/stage_07_serving/api-and-portfolio.md)
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
