# Project architecture

## Scope

This project uses modular classic RAG on Azure. The implemented offline pipeline
turns approved financial PDFs into traceable vectors. The planned online path
will retrieve evidence and return a cited answer or abstain.

Source acquisition is outside the application boundary. An operator places a
PDF in `data/sources/`; a URL is optional provenance, not a download input or
proof of permission.

| Status | Meaning |
| --- | --- |
| Implemented | Code exists in this repository. |
| Provisioned | Azure resource exists; integration may be incomplete. |
| Planned | Target capability not yet implemented. |

## System map

```mermaid
flowchart TB
    classDef implemented fill:#DCFCE7,stroke:#15803D,color:#14532D,stroke-width:2px
    classDef provisioned fill:#FEF3C7,stroke:#B45309,color:#78350F,stroke-width:2px
    classDef planned fill:#F1F5F9,stroke:#64748B,color:#334155,stroke-width:2px,stroke-dasharray:5 5

    source[Approved local PDF]
    ingest[Stage 01: register and validate]
    sourceBlob[(Immutable source blob)]
    process[Stage 02: extract and chunk]
    vectors[Stage 03: generate embeddings]
    search[(Stage 04: Azure AI Search)]
    rag[Stage 05: RAG API]
    ui[Stage 06: portfolio UI]

    source --> ingest
    ingest --> sourceBlob
    ingest --> process
    process --> vectors
    vectors --> search
    search -.-> rag
    rag -.-> ui

    class source,ingest,sourceBlob,process,vectors,search implemented
    class rag,ui planned
```

Solid arrows are implemented; dashed arrows are future integrations.

## Implemented offline path

```mermaid
flowchart TB
    classDef implemented fill:#DCFCE7,stroke:#15803D,color:#14532D,stroke-width:2px

    operator[Operator]
    pdf[PDF in data/sources]
    register[Register provenance and usage basis]
    validate[Validate path, size, PDF header and SHA-256]
    upload[Upload without overwrite]
    sourceBlob[(Blob: source-documents)]
    extract[Extract pages to processed JSON]
    chunk[Create recursive page-bounded chunks]
    request[Send embedding batches]
    model[Foundry embedding deployment]
    records[Validate and store vector records]
    entra[Microsoft Entra ID]

    operator --> pdf --> register --> validate
    validate --> upload --> sourceBlob
    validate --> extract --> chunk --> request
    request --> model --> records
    entra -.-> upload
    entra -.-> model

    class operator,pdf,register,validate,upload,sourceBlob,extract,chunk,request,model,records,entra implemented
```

Use the [source ingestion guide](../stage_01_ingestion/source-ingestion.md) for
commands. Data contracts are defined by the
[source metadata](../stage_01_ingestion/source-metadata-schema.md) and
[processed document](../stage_02_processing/processed-document-schema.md)
schemas. The [chunking strategy](../stage_02_processing/chunking-strategy.md)
records the retrieval-unit decision and comparison.

## Component status

| Component | Responsibility | Status |
| --- | --- | --- |
| `source-documents` | Preserve verified original PDFs. | Implemented |
| `processed-documents` | Store processed artifacts in Azure. | Provisioned |
| Embedding deployment | Convert text into vectors. | Implemented |
| Azure AI Search | Store the hybrid retrieval index. | Implemented |
| Chat deployment | Synthesize answers from evidence. | Provisioned |
| RAG API and UI | Retrieve, cite, and abstain. | Planned |
| `evaluation-data` | Store evaluation inputs and results. | Provisioned |
| Evaluation and telemetry | Measure quality, latency, failures, and cost. | Planned |

## Online request path (target)

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Portfolio UI
    participant API as RAG API
    participant EMB as Embedding deployment
    participant SEARCH as Azure AI Search
    participant LLM as Chat deployment

    User->>UI: Ask a finance question
    UI->>API: Send question
    API->>EMB: Generate query vector
    EMB-->>API: Query embedding
    API->>SEARCH: Run hybrid search
    SEARCH-->>API: Return chunks and source pages

    alt Evidence is sufficient
        API->>LLM: Send question and bounded evidence
        LLM-->>API: Draft cited answer
        API->>API: Validate citation IDs
        API-->>UI: Return answer and pages
    else Evidence is insufficient
        API-->>UI: Abstain
    end

    UI-->>User: Show result
```

Search is the evidence source. The API must bound context, validate citation
IDs, and abstain below a retrieval threshold.

## Security and traceability

| Context | Identity |
| --- | --- |
| Local development | Device code or browser credential with least-privilege RBAC |
| Deployed application | Managed identity with data-plane RBAC |
| Git | No credentials or document content |

```text
operator approval
  -> PDF SHA-256 + source metadata
  -> immutable source blob
  -> page hash
  -> chunk ID + chunk hash
  -> embedding record
  -> search result
  -> citation
```

Controls: restricted source paths, symlink rejection, file and hash validation,
overwrite protection, deterministic chunk IDs, vector-size checks, and
versioned schemas. `source_url` remains optional provenance. The operator is
responsible for usage and redistribution rights.

## Evaluation targets

| Layer | Measures |
| --- | --- |
| Ingestion | Hash match, extraction coverage, empty-page rate |
| Retrieval | Recall@k, MRR, nDCG, source/page match |
| Generation | Groundedness, citation correctness, abstention quality |
| Operations | p50/p95 latency, failures, tokens, estimated cost |

Each run should record corpus, index, model, retrieval, and prompt versions.

## Roadmap

1. Add the RAG API with citations and abstention.
2. Establish an expert-reviewed evaluation baseline.
3. Add the portfolio UI, managed identity, and telemetry.
