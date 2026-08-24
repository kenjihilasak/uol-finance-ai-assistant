# Project architecture

## Executive summary

This project uses a **modular classic RAG architecture on Azure**. The offline
pipeline turns operator-approved financial PDFs into traceable chunks and
embeddings. The planned online pipeline retrieves that evidence and asks the
chat model to produce cited answers or abstain.

Source acquisition is deliberately outside the application boundary. An
operator places a PDF directly in `data/sources/` and records its provenance and
usage basis. A URL is optional metadata; the application neither downloads nor
trusts a document merely because it is publicly reachable.

The diagrams use these implementation states:

- **Implemented**: code exists in this repository.
- **Provisioned**: the Azure resource exists, but application integration is
  not complete.
- **Planned**: target capability not yet implemented.

Status describes repository progress, not live Azure health.

## Logical architecture

```mermaid
flowchart LR
    classDef implemented fill:#DCFCE7,stroke:#15803D,color:#14532D,stroke-width:2px
    classDef provisioned fill:#FEF3C7,stroke:#B45309,color:#78350F,stroke-width:2px
    classDef planned fill:#F1F5F9,stroke:#64748B,color:#334155,stroke-width:2px,stroke-dasharray:5 5

    subgraph intake[Controlled local intake]
        operator[Operator]
        pdf[Approved PDF in<br/>data/sources]
        register[Register provenance,<br/>usage basis and rights note]
        validate[Validate path, extension,<br/>size, PDF header and SHA-256]

        operator --> pdf --> register --> validate
    end

    subgraph offline[Offline processing]
        upload[Upload immutable<br/>source blob]
        extract[Extract and normalise<br/>page-level text]
        chunk[Create deterministic,<br/>page-bounded chunks]
        embed[Generate and validate<br/>embedding vectors]

        validate --> upload
        validate --> extract --> chunk --> embed
    end

    subgraph azure[Azure data and AI plane]
        entra[Microsoft Entra ID]
        sourceBlob[(Blob Storage<br/>source-documents)]
        processedBlob[(Blob Storage<br/>processed-documents)]
        embeddingModel[Microsoft Foundry<br/>text-embedding-3-small]
        search[(Azure AI Search<br/>versioned hybrid index)]
        chatModel[Microsoft Foundry<br/>gpt-5-mini]
        evaluationBlob[(Blob Storage<br/>evaluation-data)]
    end

    subgraph serving[Online RAG serving]
        ui[Portfolio chat UI]
        api[API and RAG orchestrator]
        retrieve[Query embedding,<br/>hybrid retrieval and filters]
        policy[Evidence threshold,<br/>citations and abstention]

        ui --> api --> retrieve
        policy --> api
    end

    subgraph quality[Quality and operations]
        evaluator[Offline evaluation runner]
        telemetry[Logs, metrics, traces<br/>and cost signals]
    end

    upload -->|PDF + compact metadata| sourceBlob
    chunk -->|text batches| embeddingModel
    embeddingModel -->|1,536-dimensional vectors| embed
    embed -.->|processed records| processedBlob
    embed -.->|index documents| search

    retrieve -.->|embed question| embeddingModel
    retrieve -.->|vector + keyword query| search
    search -.->|top-k chunks + metadata| retrieve
    retrieve -.->|bounded evidence| chatModel
    chatModel -.->|draft answer| policy

    evaluationBlob -.-> evaluator
    evaluator -.->|test questions| api
    api -.-> telemetry
    evaluator -.-> telemetry

    entra -.->|developer OAuth + Azure RBAC| sourceBlob
    entra -.->|developer OAuth + Azure RBAC| embeddingModel
    entra -.->|managed identity + Azure RBAC| api

    class operator,pdf,register,validate,upload,extract,chunk,embed,entra,sourceBlob,embeddingModel implemented
    class processedBlob,search,chatModel,evaluationBlob provisioned
    class ui,api,retrieve,policy,evaluator,telemetry planned
```

Solid arrows are implemented data movement. Dashed arrows are target
integrations.

## Offline ingestion path

The local ingestion path is explicit and reproducible:

1. The operator places a PDF in `data/sources/`. How the operator received it
   is outside this application's scope.
2. `register_source_pdf.py` validates the local file and creates an ignored
   JSON sidecar containing a stable document ID, provenance, usage basis, rights
   note, size, SHA-256, and immutable blob name.
3. `upload_source_blob.py` verifies the PDF against its sidecar, refuses to
   overwrite a different blob, and downloads the stored object to verify its
   bytes and SHA-256. Re-running it against an identical blob is safe.
4. `extract_pdf_text.py` verifies the source again, extracts page-level text,
   and records extractor version, page hashes, normalisation rules, and an
   extraction-coverage quality gate.
5. `chunk_extracted_text.py` creates stable, page-bounded chunk identifiers.
   Each result can cite a physical PDF page.
6. `generate_embeddings.py` validates all chunks, batches their text through
   the Foundry embedding deployment, and rejects incorrectly sized vectors.

Raw PDFs, sidecars, and generated JSON remain outside Git. Scripts and schema
documentation are committed; content stays local and in controlled Azure
containers.

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
    UI->>API: POST question + correlation ID
    API->>API: Validate input and apply policy
    API->>EMB: Generate query vector
    EMB-->>API: Query embedding
    API->>SEARCH: Hybrid search with metadata filters
    SEARCH-->>API: Top-k chunks, scores and source pages

    alt Evidence passes retrieval threshold
        API->>LLM: Question + bounded evidence + citation IDs
        LLM-->>API: Grounded draft answer
        API->>API: Validate citations against retrieved chunks
        API-->>UI: Answer + source reference + page numbers
    else Evidence is insufficient
        API-->>UI: Abstain and explain what evidence is missing
    end

    UI-->>User: Cited response or explicit abstention
```

The model is not the source of truth. Search returns evidence, the chat model
synthesises only from that evidence, and the API validates citation IDs before
returning the response.

## Trust boundaries and identity

| Context | Authentication | Authorisation target |
| --- | --- | --- |
| Local development | `InteractiveBrowserCredential` in the configured tenant | Least-privilege Azure RBAC roles |
| Deployed application | Managed identity | Blob, Search, and Foundry data-plane roles |
| Git repository | No Azure credentials or document content | Templates, code, and non-secret resource names only |

Storage keys, search admin keys, connection strings, SAS tokens, access tokens,
and client secrets are not part of the intended application path. Tenant
Security Defaults remain enabled.

## Data contracts and traceability

```text
operator approval + source reference
  -> local PDF SHA-256 + metadata sidecar
  -> immutable source blob
  -> page number + page-text SHA-256
  -> deterministic chunk ID + chunk-text SHA-256
  -> embedding record
  -> search result
  -> answer citation
```

Important controls include:

- source files restricted to `data/sources/`, with symlinks rejected;
- format-header, size, metadata, and SHA-256 validation at stage boundaries;
- immutable blob names and overwrite protection;
- versioned source and processed-document schemas;
- deterministic, page-bounded chunks;
- provenance and rights notes carried into processed artifacts;
- explicit vector-dimension validation;
- a versioned search index name for safe schema evolution.

`source_url` is nullable and retained only for provenance. It is not used for
download or as proof of permission. The operator remains responsible for
confirming that processing and any displayed excerpts are allowed.

See [processed-document-schema.md](./processed-document-schema.md) for the
current extraction contract,
[source-metadata-schema.md](./source-metadata-schema.md) for the registration
contract, and [../source-ingestion.md](../source-ingestion.md) for the executable
workflow.

## Retrieval and answer policy

The target uses hybrid retrieval:

- keyword search preserves exact financial terms, dates, and account names;
- vector search captures semantically related language;
- metadata filters can exclude historical documents;
- semantic reranking can be measured separately from the baseline;
- an evidence threshold triggers abstention when the corpus is insufficient.

The API must constrain context size, validate citation identifiers, and expose
the source reference and physical page number. A source URL is shown only when
one was recorded.

## Evaluation strategy

The `evaluation-data` container will hold versioned questions, expected
evidence, and run results.

| Layer | Example measures |
| --- | --- |
| Ingestion | source hash match, extraction coverage, empty-page rate |
| Retrieval | Recall@k, MRR, nDCG, source/page match |
| Generation | groundedness, citation correctness, answer relevance, abstention quality |
| Operations | p50/p95 latency, request failures, token usage, estimated cost |

Each run should record corpus version, index version, embedding deployment,
retrieval settings, prompt version, and chat deployment.

## Delivery roadmap

1. **Implemented foundation**: controlled local registration, verified Blob
   upload, extraction, deterministic chunking, and embedding generation.
2. **Retrieval MVP**: define the Azure AI Search schema, upload vectors, and
   verify keyword, vector, and hybrid retrieval from Python.
3. **Grounded answer MVP**: add the RAG orchestrator, citations, evidence
   thresholds, and explicit abstention.
4. **Evaluation**: create an expert-reviewed dataset and establish retrieval
   baselines before prompt tuning.
5. **Serving and operations**: expose an authenticated API and portfolio UI,
   deploy with managed identity, and add telemetry and cost monitoring.
