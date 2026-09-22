# Classification contract

The classifier is the first Azure model call in the triage pipeline. Its
implementation is
[`classify_enquiry.py`](../../scripts/stage_06_triage/classify_enquiry.py).

## Input and output

GPT-5-mini receives:

- the original enquiry;
- classification instructions; and
- a strict JSON Schema.

It must return:

```text
summary · category · subcategory · is_sensitive
proposed action · proposed route · missing information
```

The validated Python models and enums live in
[`schemas.py`](../../scripts/stage_06_triage/schemas.py). The model cannot add
fields or invent category, action, or route values.

## Categories

| Category | Meaning | RAG corpus |
| --- | --- | --- |
| `finance` | Annual-report information | Yes |
| `finance_operations` | Expenses and travel guidance | Yes |
| `student_admin` | Personal-details and address guidance | Yes |
| `digital_learning` | Minerva and online-learning guidance | Yes |
| `unsupported` | Outside the approved knowledge scope | No |

`unsupported` is a control value, not a fifth knowledge corpus. Sensitivity and
missing information are independent fields, so they are not categories.

For a mixed sensitive enquiry, the classifier retains the supported knowledge
category when one applies. A stalking-related address request can therefore be
`student_admin` and `is_sensitive=true`; the safety policy still blocks RAG.

## Defence in depth

[`sensitive_rules.py`](../../scripts/stage_06_triage/sensitive_rules.py) runs
before classification. Its flags do not replace the model result: both are
passed to the routing policy so either layer can trigger a safe escalation.

Return to the [triage overview](enquiry-triage.md) or continue to the
[routing and safety policy](routing-policy.md).
