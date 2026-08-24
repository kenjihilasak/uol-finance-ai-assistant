# UoL Finance AI Assistant

An explainable Azure RAG portfolio project for question answering over
operator-approved financial PDFs. The project emphasises provenance,
deterministic processing, Entra ID authentication, cited evidence, and
measurable retrieval quality.

## Current status

Implemented locally:

- direct PDF registration, validation, SHA-256, and duplicate detection;
- immutable verified upload to Azure Blob Storage;
- page-level extraction with a text-coverage quality gate;
- deterministic page-bounded chunking;
- batched embeddings through a Microsoft Foundry deployment.

Provisioned for the next milestones:

- Azure AI Search for hybrid retrieval;
- a Foundry chat deployment for grounded answers;
- Blob containers for processed artifacts and evaluation data.

The Azure AI Search indexer, RAG API, evaluation runner, and UI remain planned.
Architecture diagrams distinguish implemented, provisioned, and planned parts
so the repository does not present roadmap items as finished work.

## Local workflow

PDF input starts here:

```text
data/sources/<document>.pdf
```

The application does not download PDFs from URLs. Follow the
[source ingestion guide](./docs/source-ingestion.md) to register and process a
file. PDFs, metadata sidecars, extracted text, chunks, embeddings, `.env`, and
credentials are ignored by Git.

## Documentation

Start with the [documentation index](./docs/README.md) and
[project architecture](./docs/architecture/project-architecture.md). The
[scripts guide](./scripts/README.md) explains the stage-based folder structure
and module commands.

## Authentication and secrets

Local Azure access uses Microsoft Entra ID with
`InteractiveBrowserCredential`. Copy `.env.example` to `.env` for local resource
configuration. Never commit storage keys, search admin keys, connection
strings, SAS tokens, access tokens, or client secrets. A deployed service should
use managed identity and least-privilege RBAC.

## Run tests

```bash
python -m unittest discover -s tests -v
```
