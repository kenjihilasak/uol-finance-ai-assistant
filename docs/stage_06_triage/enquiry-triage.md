# Enquiry triage and safe routing

The user is a staff member handling an incoming enquiry. The person who sent
the original email never interacts with the demo directly.

## Decision flow

```text
unstructured enquiry
        |
        v
conservative sensitive-term rules ---- match ---> specialist referral
        |                                         no retrieval or generation
        v
structured LLM classification -------- sensitive -> specialist referral
        |
        +-- unclear or missing information ------> clarification request
        |
        +-- unsupported domain ------------------> manual review
        |
        `-- approved answerable domain ----------> category-filtered RAG
                                                   staff-reviewed draft + citations
```

The LLM returns a typed classification: `category`, `subcategory`,
`is_sensitive`, proposed `action`, `route_to`, `missing_info`, and a short
summary. `routing_policy.py` then makes the final decision in code. A sensitive
decision always sets `allow_generation=false`, so the model never receives
retrieved context with which to draft a response.

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

The safety gates are `sensitive_recall=1.0` and
`sensitive_generation_leaks=0`. Category, action, and route accuracy are useful
quality metrics but do not replace the safety assertions.

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
