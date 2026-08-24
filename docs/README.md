# Documentation learning path

The documentation mirrors the executable pipeline. Start with the two overview
documents, then move through the numbered stages in the same order as
[`scripts/`](../scripts/README.md).

```text
docs/
├── overview/              # System design and RAG rationale
├── stage_00_environment/  # Azure resources, identity, and secret boundaries
├── stage_01_ingestion/    # Local PDF intake, provenance, and source schema
├── stage_02_processing/   # Page-level extraction contract
└── stage_03_embeddings/   # Vector generation contract and execution
```

## Recommended reading order

1. [Project architecture](./overview/project-architecture.md) — see the whole
   offline and planned online system before studying individual scripts.
2. [RAG approach](./overview/rag-approach.md) — understand why the project uses
   direct PDF intake and a custom classic RAG baseline.
3. [Azure resources](./stage_00_environment/azure-resources.md) — learn what
   each provisioned resource does and where authentication boundaries sit.
4. [Source ingestion guide](./stage_01_ingestion/source-ingestion.md) — follow
   the executable workflow for registering and uploading one approved PDF.
5. [Source metadata schema](./stage_01_ingestion/source-metadata-schema.md) —
   inspect the provenance and integrity contract created during registration.
6. [Processed document schema](./stage_02_processing/processed-document-schema.md)
   — understand page-level output before reading the chunking implementation.
7. [Embedding generation](./stage_03_embeddings/embedding-generation.md) —
   understand validation, Azure calls, and the vector output contract.

For hands-on learning, read one stage document and then inspect or run the
matching module under `scripts/stage_*`. Avoid reading every schema first; the
contracts are easier to understand after seeing the artifact produced by the
previous stage.

## Current documentation boundary

Only implemented pipeline stages receive numbered folders. Azure AI Search
indexing, retrieval, answer generation, evaluation, and serving remain in the
architecture roadmap. Their documentation will be added with their code so
planned behavior is not confused with completed functionality.
