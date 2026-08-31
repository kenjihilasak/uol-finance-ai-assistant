# Azure AI Search Index Creation

This script creates the Azure AI Search index for the UoL Finance AI Assistant project.

## Usage

```bash
# Validate configuration without creating the index
python -m scripts.stage_04_search_index.create_index --dry-run

# Create the actual index
python -m scripts.stage_04_search_index.create_index
```

## Configuration

The script uses the following environment variables from `.env`:
- `AZURE_SEARCH_ENDPOINT`: Azure AI Search service endpoint
- `AZURE_SEARCH_INDEX_NAME`: Versioned index name
- `AZURE_TENANT_ID`: Your Azure tenant ID for Entra ID authentication
- `AZURE_EMBEDDING_DIMENSIONS`: Vector dimensions; currently 1,536

## Index Schema

The index schema follows the specification in [index-schema.md](index-schema.md).

It includes:
- Standard text fields for searchable content
- Metadata fields for filtering and sorting
- A vector field for semantic similarity search
- Complex type fields for page and character ranges

Creation is protected against accidental replacement: the script uses
`create_index`, so an existing index causes an error instead of being updated.
