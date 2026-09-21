# Documentation learning path

Read the overview first, then follow the same stage order as
[`scripts/`](../scripts/README.md).

```text
docs/
├── overview/
├── stage_00_environment/
├── stage_01_ingestion/
├── stage_02_processing/
├── stage_03_embeddings/
├── stage_04_search_index/
├── stage_05_retrieval/
├── stage_06_triage/
└── stage_07_serving/
```

## Reading order

1. [Project architecture](./overview/project-architecture.md)
2. [RAG approach](./overview/rag-approach.md)
3. [Corpus and routing boundaries](./overview/corpus-and-routing.md)
4. [Azure resources](./stage_00_environment/azure-resources.md)
5. [Source ingestion](./stage_01_ingestion/source-ingestion.md)
6. [Source metadata schema](./stage_01_ingestion/source-metadata-schema.md)
7. [Processed document schema](./stage_02_processing/processed-document-schema.md)
8. [Chunking strategy](./stage_02_processing/chunking-strategy.md)
9. [Embedding generation](./stage_03_embeddings/embedding-generation.md)
10. [Index schema](./stage_04_search_index/index-schema.md)
11. [Create index guide](./stage_04_search_index/create-index.md)
12. [Upload documents guide](./stage_04_search_index/upload-documents.md)
13. [Hybrid retrieval](./stage_05_retrieval/hybrid-retrieval.md)
14. [Retrieval design decisions](./stage_05_retrieval/retrieval-design-decisions.md)
15. [Retrieval evaluation](./stage_05_retrieval/retrieval-evaluation.md)
16. [Grounded answer generation](./stage_05_retrieval/grounded-answer-generation.md)
17. [Enquiry triage and safety](./stage_06_triage/enquiry-triage.md)
18. [Portfolio UI options](./overview/ui-options.md)
19. [Architecture options: current, Azure-native, and Power Platform](./overview/architecture-options.md)
20. [Serving API and portfolio](./stage_07_serving/api-and-portfolio.md)
21. [Staff authentication](./stage_07_serving/staff-authentication.md)

For hands-on learning, read one stage and then run its matching module.
