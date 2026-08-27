# Documentation learning path

Read the overview first, then follow the same stage order as
[`scripts/`](../scripts/README.md).

```text
docs/
├── overview/
├── stage_00_environment/
├── stage_01_ingestion/
├── stage_02_processing/
└── stage_03_embeddings/
```

## Reading order

1. [Project architecture](./overview/project-architecture.md)
2. [RAG approach](./overview/rag-approach.md)
3. [Azure resources](./stage_00_environment/azure-resources.md)
4. [Source ingestion](./stage_01_ingestion/source-ingestion.md)
5. [Source metadata schema](./stage_01_ingestion/source-metadata-schema.md)
6. [Processed document schema](./stage_02_processing/processed-document-schema.md)
7. [Chunking strategy](./stage_02_processing/chunking-strategy.md)
8. [Embedding generation](./stage_03_embeddings/embedding-generation.md)

For hands-on learning, read one stage and then run its matching module. Search
indexing, retrieval, evaluation, and serving docs will be added with their code.
