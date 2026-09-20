# Corpus and routing boundaries

The staff tool separates answerable operational knowledge from sensitive cases
that must be routed without an AI-generated substantive response.

| Domain | Behaviour | Current source status |
| --- | --- | --- |
| `finance` | Corporate reporting answers with citations | Indexed |
| `student_admin` | Process guidance with citations | Indexed |
| `digital_learning` | Minerva and online-learning guidance | Indexed |
| `finance_operations` | Expense-policy guidance | Indexed |
| `student_support` | Specialist referral only | Routing sources registered |

`config/public_documents.json` is the allowlist for answerable sources.
`config/specialist_routes.json` holds referral destinations with
`generation_allowed=false`. Sensitive enquiries must never enter retrieval or
answer generation.

The Finance website rejected automated acquisition from this runtime. An
operator saved approved local snapshots, which were hashed, processed, embedded,
and indexed without committing the source content to Git.
