# Embedding generation

Stage 03 converts chunk text into vectors. It does not update Azure AI Search.

## Input validation

Input: `data/processed/<document-id>.chunks.json`.

Before calling Azure, the module requires one document ID, non-empty chunks,
unique chunk IDs, matching document IDs, and non-empty text.

```bash
python -m scripts.stage_03_embeddings.generate_embeddings \
  --input data/processed/<document-id>.chunks.json \
  --dry-run
```

## Configuration

| `.env` variable | Purpose |
| --- | --- |
| `AZURE_TENANT_ID` | Entra tenant |
| `AZURE_OPENAI_ENDPOINT` | OpenAI-compatible Foundry endpoint |
| `AZURE_EMBEDDING_DEPLOYMENT` | Embedding deployment name |
| `AZURE_EMBEDDING_DIMENSIONS` | Required vector length |

Authentication uses `InteractiveBrowserCredential`, not API keys. Requests use
batches of 16; vectors with the wrong dimensions are rejected.

## Generate

```bash
python -m scripts.stage_03_embeddings.generate_embeddings \
  --input data/processed/<document-id>.chunks.json
```

Output: `data/processed/<document-id>.embeddings.json`.

| Output field | Purpose |
| --- | --- |
| `schema_version` | Contract version |
| `document_id` | Source document link |
| `source_chunks_sha256` | Complete chunk-file hash |
| `embedding_deployment` | Deployment used |
| `embedding_dimensions` | Vector length |
| `records` | Chunk fields plus `content_vector` |

Existing output requires `--overwrite`. Stage 04 will define the Azure AI
Search schema and upload these records.
