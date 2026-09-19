# Azure AI Search Index Schema

## Overview

The index supports BM25 + vector retrieval across multiple document categories.
`category` is metadata: it is used for filtering, sorting, and facets rather
than keyword matching.

## Field Properties

### Searchable Fields
Fields that support full-text search:
- `text` - Extracted content for keyword matching
- `embedding_text` - Extended context text for keyword search
- `source_title` - Document titles for search
- `institution` - Organization names for search
- `source_reference` - Reference information for search
- `source_url` - Source URLs for search
- `status` - Document status for search
- `embedding_deployment` - Model identifiers for search

### Filterable Fields
Fields that can be used in `$filter` queries:
- `document_id` - Filter by document
- `chunk_id` - Filter by specific chunks
- `page_number` - Filter by page numbers
- `institution` - Filter by organization
- `document_date` - Filter by date ranges
- `status` - Filter by document status
- `source_url` - Filter by source URLs
- `source_sha256` - Filter by document hash
- `text_sha256` - Filter by text content hash
- `embedding_text_sha256` - Filter by embedding text hash
- `embedding_deployment` - Filter by embedding model
- `category` - Filter document families such as `finance` or `student_admin`

### Sortable Fields
Fields that can be used in `$orderby` queries:
- `document_id` - Sort results by document
- `chunk_id` - Sort results by chunk
- `page_number` - Sort by page order
- `document_date` - Sort by document dates
- `source_title` - Sort alphabetically by title
- `category` - Sort by document family

### Facetable fields

- `category` - Count and display available document families

### Retrievable Fields
Text and metadata fields are retrievable for citations and provenance. The
vector is not returned in search responses because it is large and has no UI
or citation value.

The final creation script sets `content_vector.retrievable` to `false`. The
existing `uol-finance-chunks-v1` index was created during development with that
property set to `true`; Stage 05 queries must therefore use an explicit `select`
list that excludes `content_vector`. Apply the final schema through a versioned
replacement index rather than deleting the working index in place.

### Vector Fields
Fields supporting semantic similarity search:
- `content_vector` - The 1,536-dimensional embedding vector using the HNSW
  cosine profile

## Field Mappings

Most fields map directly from the embeddings JSON records array:
- `records[i].document_id` → `document_id`
- `records[i].chunk_id` → `chunk_id`
- `records[i].page_number` → `page_number`
- `records[i].text` → `text`
- `records[i].embedding_text` → `embedding_text`
- `records[i].source_title` → `source_title`
- `records[i].institution` → `institution`
- `records[i].category` → `category`
- `records[i].source_reference` → `source_reference`
- `records[i].source_url` → `source_url`
- `records[i].document_date` → `document_date`
- `records[i].status` → `status`
- `records[i].source_sha256` → `source_sha256`
- `records[i].text_sha256` → `text_sha256`
- `records[i].embedding_text_sha256` → `embedding_text_sha256`
- `records[i].content_vector` → `content_vector`
- Root level `embedding_deployment` → `embedding_deployment`

`schema_version` is pipeline metadata and is intentionally not indexed.
`document_date` is normalised to a UTC `DateTimeOffset` during upload.

Complex type mappings:
- `records[i].page_range` → `page_range` (Edm.ComplexType)
- `records[i].character_range` → `character_range` (Edm.ComplexType)
