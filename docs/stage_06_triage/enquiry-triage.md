# Enquiry triage and safe routing

The user is a staff member handling an incoming enquiry. The person who sent
the original email never interacts with the demo directly.

## Decision flow

```text
Staff browser — GitHub Pages
        │
        │ Unstructured enquiry
        ▼
FastAPI — Railway
        │
        ├── Request validation and authentication
        │
        ├── Deterministic sensitive-term scan in Python
        │       └── Rule flags retained
        │
        ├── Azure call 1: GPT-5-mini classification
        │       └── Category, sensitivity, route and missing information
        │
        └── Deterministic routing policy in Python
                │
                ├── Sensitive
                │     └── Specialist referral; stop
                │
                ├── Missing information
                │     └── Request clarification; stop
                │
                ├── Unsupported category
                │     └── Manual review; stop
                │
                └── Approved category
                      │
                      ├── Azure call 2:
                      │   Original enquiry → text-embedding-3-small
                      │   → 1,536-dimensional query vector
                      │
                      ├── Azure call 3: Azure AI Search
                      │
                      │   Stored index:
                      │   - Chunk text for lexical search
                      │   - Chunk vectors for similarity search
                      │   - Source and category metadata
                      │
                      │   Query inputs:
                      │   - Original enquiry text
                      │   - Query vector
                      │   - Exact category filter
                      │
                      │   Hybrid retrieval:
                      │   - BM25 lexical search over stored chunk text
                      │   - HNSW semantic search over stored chunk vectors
                      │   - RRF combines both ranked lists
                      │   - 50 vector candidates considered
                      │   - Top 5 fused chunks returned
                      │
                      ├── Evidence preparation in FastAPI
                      │   - Assign controlled source IDs
                      │   - Preserve source title, URL and page
                      │   - Limit evidence text
                      │
                      ├── Azure call 4: GPT-5-mini grounded generation
                      │
                      │   Inputs:
                      │   - Original enquiry
                      │   - Top 5 evidence chunks
                      │   - Allowed citation IDs
                      │
                      └── Staff-reviewed draft + citations
                              │
                              ├── Response returned to browser
                              └── Stored in Railway PostgreSQL
                                  only when staff is authenticated
```

The LLM returns a typed classification: `category`, `subcategory`,
`is_sensitive`, proposed `action`, `route_to`, `missing_info`, and a short
summary. `routing_policy.py` then makes the final decision in code. A sensitive
decision always sets `allow_generation=false`, so the model never receives
retrieved context with which to draft a response.

The sensitive-term scan runs first inside FastAPI on Railway, but the current
implementation still sends the enquiry to GPT-5-mini for classification. The
routing policy then combines the retained rule flags with the LLM result. A
sensitive result stops calls 2–4: no query embedding, retrieval, or draft
generation occurs.

Azure AI Search stores both chunk text and vectors. Citations originate from
the returned chunks' `source_title`, `source_url`, `page_number`, and text
metadata. FastAPI assigns allowed IDs such as `S1`; GPT-5-mini may cite only
those IDs, and FastAPI validates them before returning the response.

## Files

| File | Responsibility |
| --- | --- |
| `schemas.py` | Validated classification and decision contracts |
| `sensitive_rules.py` | Conservative first-layer safety flags |
| `classify_enquiry.py` | Structured classification with `gpt-5-mini` |
| `routing_policy.py` | Deterministic final action and route |
| `triage_enquiry.py` | Orchestrates classification and approved RAG |
| `evaluate_triage.py` | Measures the ten-case reviewed dataset |

## Evaluation

The canonical report combines retrieval results with the expanded 21-case
triage and safety evaluation:
[System evaluation](../stage_05_retrieval/retrieval-evaluation.md).

The dataset contains synthetic enquiries only. Do not enter real personal or
sensitive correspondence in the portfolio demo.
