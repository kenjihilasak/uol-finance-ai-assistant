# Embedding generation

Stage 03 converts deterministic text chunks into vectors using the configured
Microsoft Foundry embedding deployment. It does not create or update an Azure
AI Search index.

## Input

The module accepts one Stage 02 chunk artifact:

```text
data/processed/<document-id>.chunks.json
```

Before any Azure call, it verifies that:

- the payload has one `document_id` and a non-empty `chunks` list;
- every chunk belongs to that document;
- every `chunk_id` is unique;
- every chunk contains non-empty text.

Use a dry run to perform only these local checks:

```bash
python -m scripts.stage_03_embeddings.generate_embeddings \
  --input data/processed/<document-id>.chunks.json \
  --dry-run
```

## Azure configuration

Generation reads these values from the ignored local `.env` file:

| Variable | Purpose |
| --- | --- |
| `AZURE_TENANT_ID` | Tenant used for interactive Entra authentication. |
| `AZURE_OPENAI_ENDPOINT` | OpenAI-compatible Foundry resource endpoint. |
| `AZURE_EMBEDDING_DEPLOYMENT` | Deployment name sent as the API model. |
| `AZURE_EMBEDDING_DIMENSIONS` | Required size of every returned vector. |

The module uses `InteractiveBrowserCredential`; it does not accept API keys.
Chunks are sent in batches of 16 and each returned vector is rejected if its
length differs from `AZURE_EMBEDDING_DIMENSIONS`.

## Execution and output

```bash
python -m scripts.stage_03_embeddings.generate_embeddings \
  --input data/processed/<document-id>.chunks.json
```

The ignored output is:

```text
data/processed/<document-id>.embeddings.json
```

Its top-level contract contains:

| Field | Purpose |
| --- | --- |
| `schema_version` | Version of the embedding artifact contract. |
| `document_id` | Links all records to the registered source. |
| `source_chunks_sha256` | Detects changes to the complete chunk input. |
| `embedding_deployment` | Records which configured deployment was called. |
| `embedding_dimensions` | Records the required vector length. |
| `records` | Original chunk fields plus `content_vector`. |

The module does not overwrite an existing output unless `--overwrite` is
explicitly supplied. Stage 04 will define the versioned Azure AI Search schema
and upload these records when that implementation begins.
