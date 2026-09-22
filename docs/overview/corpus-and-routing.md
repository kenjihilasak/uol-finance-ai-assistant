# Corpus and routing boundaries

The classifier exposes five category values, but only four have an approved RAG
corpus.

| Category | Knowledge scope | RAG |
| --- | --- | --- |
| `finance` | University annual-report information | Allowed |
| `finance_operations` | Expenses, travel and subsistence guidance | Allowed |
| `student_admin` | Personal-details and address guidance | Allowed |
| `digital_learning` | Minerva and online-learning guidance | Allowed |
| `unsupported` | Everything outside the approved scope | Blocked |

Sensitivity and missing information are independent fields, not categories.
They can block RAG even when the category is otherwise supported.

Two tracked controls define the boundary:

- [`public_documents.json`](../../config/public_documents.json) allowlists
  answerable sources and their official URLs.
- [`specialist_routes.json`](../../config/specialist_routes.json) defines
  referral destinations where generation is prohibited.

The source corpus is operator-approved. Public availability is treated as
provenance, not permission to redistribute. Original and generated artifacts
remain outside Git.

See [enquiry triage](../stage_06_triage/enquiry-triage.md) for routing and
[source ingestion](../stage_01_ingestion/source-ingestion.md) for intake.
