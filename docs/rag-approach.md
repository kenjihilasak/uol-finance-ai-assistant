# Portfolio RAG approach

This is a small, explainable RAG portfolio project over official University of
Leeds financial documents. It is deliberately a custom pipeline rather than a
copy of a full application template.

## Chosen approach

1. Keep the verified source PDF and extracted JSON as traceable local inputs.
2. Create deterministic, page-bounded chunks with source metadata.
3. Generate embeddings locally with the Foundry embedding deployment.
4. Upload chunk records and vectors to one Azure AI Search index.
5. Retrieve the best chunks and show their source page in a later chat view.

The next implementation step is step 3. No Azure AI Search index or embedding
call is made by this document.

## Azure references used as patterns

- `Azure-Samples/azure-search-classic-rag` informs the simple classic RAG flow:
  chunk, embed, index, retrieve, then generate an answer.
- `Azure-Samples/azure-search-python-samples` informs the later vector index and
  push-upload code.

We are not adopting the full `azure-search-openai-demo` template yet. It is a
useful reference for a future citation-enabled UI, but it also adds deployment
infrastructure and a complete frontend that are outside this portfolio stage.

## Endpoint boundary

`FOUNDRY_PROJECT_ENDPOINT` identifies the Foundry project. Embeddings use the
separate OpenAI-compatible endpoint configured as `AZURE_OPENAI_ENDPOINT`.
All local authentication remains Microsoft Entra ID; no API keys, connection
strings, or SAS tokens are used.
