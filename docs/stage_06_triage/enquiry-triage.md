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

Validate the dataset without contacting Azure:

```bash
python -m scripts.stage_06_triage.evaluate_triage
```

Run the reviewed ten-case baseline against Azure:

```bash
python -m scripts.stage_06_triage.evaluate_triage \
  --live \
  --output evaluation/baselines/triage_v1.json
```

The primary safety gates are `sensitive_recall=1.0` and
`sensitive_generation_leaks=0`. Version 2 also measures sensitivity precision
and specificity so a system cannot appear safe merely by marking every case as
sensitive. Category, action, route, and generation-gate accuracy measure
separate behaviour and do not replace the safety assertions.

Baseline recorded on 20 September 2026:

| Metric | Result |
| --- | ---: |
| Category accuracy | 1.00 |
| Action accuracy | 1.00 |
| Route accuracy | 0.80 |
| Sensitive recall | 1.00 |
| Sensitive generation leaks | 0 |

The two route disagreements were non-safety cases: the classifier selected
`online_learning_support` rather than `it_service_desk` for an incomplete
Minerva enquiry, and `none` rather than `manual_triage` for a wholly unclear
message. Both still produced the required clarification action and blocked
generation. See
[`triage_v1.json`](../../evaluation/baselines/triage_v1.json) for all outputs.

The dataset uses synthetic enquiries only. Do not copy real personal or
sensitive correspondence into the portfolio demo.

## Expanded triage evaluation

`uol-staff-triage-v2` expands the set from 10 to 21 synthetic cases. It covers
all answerable categories, missing-information gates, three specialist routes,
mixed intent, implicit sensitive language, ambiguity, and a non-incident use
of sensitive policy terminology.

| Metric | Version 2 result |
| --- | ---: |
| Cases | 21 |
| Category accuracy | 1.000 |
| Action accuracy | 0.905 |
| Route accuracy | 0.762 |
| Generation-gate accuracy | 0.952 |
| Sensitive recall | 1.000 |
| Sensitive precision | 0.857 |
| Sensitive specificity | 0.933 |
| Sensitive false positives | 1 |
| Sensitive generation leaks | 0 |

The conservative rules correctly blocked generation for all six sensitive
cases. They also flagged one non-incident research question containing the word
`harassment`, producing a false positive and specialist referral. This is a
known precision trade-off, not a hidden success. A production revision should
add reviewed contextual/negation cases and decide with domain owners whether
policy-research enquiries should go to manual review or remain conservatively
referred.

Six cases contain at least one expected-field disagreement across action and
route labels. These
include finance-information versus finance-team routing and IT service desk
versus online-learning support. The safe generation decision was still correct
for 20 of 21 cases. Route ownership requires domain agreement before it can be
treated as an objective production label.

Artifacts:

- [Expanded dataset](../../evaluation/datasets/triage_cases_v2.json)
- [Versioned baseline](../../evaluation/baselines/triage_v2.json)
- [Independent-review template](../../evaluation/reviews/independent_domain_review.md)

Run it with:

```bash
python -m scripts.stage_06_triage.evaluate_triage \
  --dataset evaluation/datasets/triage_cases_v2.json \
  --live --output data/evaluation/triage_v2.results.json
```
