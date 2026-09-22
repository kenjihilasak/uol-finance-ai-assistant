# Corpus and routing boundaries

The staff tool separates answerable operational knowledge from sensitive cases
that must be routed without an AI-generated substantive response.

| Classification category | Behaviour | Current source status |
| --- | --- | --- |
| `finance` | Corporate reporting answers with citations | Indexed |
| `student_admin` | Process guidance with citations | Indexed |
| `digital_learning` | Minerva and online-learning guidance | Indexed |
| `finance_operations` | Expense-policy guidance | Indexed |
| `unsupported` | Manual review or sensitive specialist referral | No RAG corpus |

`config/public_documents.json` is the allowlist for answerable sources.
`unsupported` is a control value, not a fifth knowledge corpus.
`config/specialist_routes.json` holds referral destinations with
`generation_allowed=false`. Sensitivity is a separate boolean condition;
sensitive enquiries must never enter retrieval or answer generation.

The Finance website rejected automated acquisition from this runtime. An
operator saved approved local snapshots, which were hashed, processed, embedded,
and indexed without committing the source content to Git.
