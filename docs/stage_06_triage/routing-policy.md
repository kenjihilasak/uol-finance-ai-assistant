# Routing and safety policy

[`routing_policy.py`](../../scripts/stage_06_triage/routing_policy.py) makes the
final decision in deterministic Python. The LLM output is a proposal, not the
authority that enables generation.

## Precedence

Rules are applied in this order:

| Priority | Condition | Final action | Final route | RAG |
| ---: | --- | --- | --- | --- |
| 1 | Python or LLM marks the enquiry sensitive | `specialist_referral` | Controlled specialist team | Blocked |
| 2 | Category is `unsupported` | `manual_review` | `manual_triage` | Blocked |
| 3 | Supported but essential information is missing | `request_clarification` | Proposed operational team | Blocked |
| 4 | Supported and complete | `draft_response` | Proposed operational team | Allowed |

This ordering prevents a model-proposed `draft_response` from overriding a
sensitive rule, unsupported scope, or missing-information gate.

## Staff decision for incomplete enquiries

For a supported but incomplete enquiry, the Staff UI displays:

```text
missing_info · route_to · recommended action
```

The staff member decides whether to request the missing information or route
the enquiry to the proposed operational team. The system does not generate a
substantive response first.

## Generation boundary

[`triage_enquiry.py`](../../scripts/stage_06_triage/triage_enquiry.py) checks
`allow_generation`. A blocked case creates no query embedding, performs no
Azure AI Search retrieval, and generates no draft. Only a supported, complete,
non-sensitive enquiry enters category-filtered RAG.

Specialist destinations are controlled in
[`specialist_routes.json`](../../config/specialist_routes.json). Authenticated
results enter the staff queue; sensitive raw enquiry text is redacted from
persistence.

The behaviour is tested by
[`evaluate_triage.py`](../../scripts/stage_06_triage/evaluate_triage.py) against
the reviewed 21-case dataset. See the [triage evaluation](triage-evaluation.md)
for current metrics, or return to the [triage overview](enquiry-triage.md).
