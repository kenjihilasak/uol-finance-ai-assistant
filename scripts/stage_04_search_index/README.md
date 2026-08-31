# Stage 04: Search Index

This stage implements Azure AI Search indexing for the UoL Finance AI Assistant project.

## Components

1. `create_index.py` - Creates the Azure AI Search index with the proper schema
2. `upload_documents.py` - Uploads document embeddings to the search index

## Prerequisites

- Completed stages 01-03 (registration, processing, and embeddings)
- Azure AI Search service provisioned
- `.env` configured with `AZURE_SEARCH_ENDPOINT` and
  `AZURE_SEARCH_INDEX_NAME`

## Environment Variables

```bash
AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AZURE_SEARCH_INDEX_NAME=uol-finance-chunks-v1
AZURE_TENANT_ID=your-tenant-id
```

## Usage

### Create Index

```bash
# Dry run to validate configuration
python -m scripts.stage_04_search_index.create_index --dry-run

# Create the actual index
python -m scripts.stage_04_search_index.create_index
```

### Upload Documents

```bash
# Dry run to validate configuration
python -m scripts.stage_04_search_index.upload_documents --input data/processed/document.embeddings.json --index-name uol-finance-chunks-v1 --dry-run

# Upload embeddings to the index
python -m scripts.stage_04_search_index.upload_documents --input data/processed/document.embeddings.json --index-name uol-finance-chunks-v1
```

## Index Schema

The index schema is documented in [../../docs/stage_04_search_index/index-schema.md](../../docs/stage_04_search_index/index-schema.md).

## Detailed Documentation

- [Create Index Guide](../../docs/stage_04_search_index/create-index.md)
- [Upload Documents Guide](../../docs/stage_04_search_index/upload-documents.md)
