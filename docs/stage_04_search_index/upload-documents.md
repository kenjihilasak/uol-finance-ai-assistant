# Azure AI Search Document Upload

This script uploads document embeddings to the Azure AI Search index.

## Usage

```bash
# Validate configuration without uploading documents
python -m scripts.stage_04_search_index.upload_documents --input data/processed/document.embeddings.json --index-name uol-finance-chunks-v1 --dry-run

# Upload embeddings to the index
python -m scripts.stage_04_search_index.upload_documents --input data/processed/document.embeddings.json --index-name uol-finance-chunks-v1
```

## Configuration

The script uses the following environment variables from `.env`:
- `AZURE_SEARCH_ENDPOINT`: Azure AI Search service endpoint
- `AZURE_TENANT_ID`: Your Azure tenant ID for Entra ID authentication

## Input Format

The script expects embeddings in the JSON format produced by stage 03:
- `records`: Array of document chunks with embeddings
- Each record contains searchable text, metadata, and a content vector

Before contacting Azure, every record is mapped to the exact index contract:

- `schema_version` and other pipeline-only fields are excluded.
- Root-level `embedding_deployment` is copied into each search document.
- `document_date` is converted from `YYYY-MM-DD` to UTC `DateTimeOffset`.
- `page_range` and `character_range` retain only integer `start` and `end`.
- `content_vector` must contain exactly 1,536 finite numeric values.
- Null `source_url` values are omitted.

The dry run performs this mapping for every record without authenticating or
uploading:

```bash
python -m scripts.stage_04_search_index.upload_documents \
  --input data/processed/<document-id>.embeddings.json \
  --index-name uol-finance-chunks-v1 \
  --dry-run
```

## Batch Processing

Documents are uploaded in batches of 100. The command fails if Azure rejects
any individual document and verifies the final successful-result count.
