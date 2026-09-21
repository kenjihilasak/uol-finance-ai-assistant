# Retrieval evaluation

## Dataset

`uol-finance-retrieval-v1` contains 10 questions covering financial tables,
financial narrative, research, pensions, scholarships, sustainability, and
governance. Each question has a concise reference answer, expected pages, and
one or more source-verified relevant chunk IDs.

The dataset contains no copied passages or vectors:
[`retrieval_questions_v1.json`](../../evaluation/datasets/retrieval_questions_v1.json).

## Metrics

- Question-level Recall@k: fraction of questions with at least one relevant
  chunk in the first `k` results.
- MRR@5: **Mean Reciprocal Rank** within the top five. For each question, take
  `1 / first relevant rank`, use zero for a miss, then calculate the arithmetic
  mean across questions.

`Mean` means arithmetic average, not median. The median would select the middle
reciprocal-rank value after sorting and is not part of MRR.

These metrics evaluate retrieval only. They do not measure answer correctness,
groundedness, citations, or abstention.

## Baseline comparison

Both runs use the same 10 questions, `top=5`, 50 vector candidates,
`text-embedding-3-small`, and index `uol-finance-chunks-v1`.

| Metric | Vector only | Hybrid BM25 + vector |
| --- | ---: | ---: |
| Recall@1 | 0.500 | 0.700 |
| Recall@3 | 0.900 | 0.900 |
| Recall@5 | 0.900 | 1.000 |
| MRR@5 | 0.683 | 0.825 |

Hybrid retrieval improves early ranking and finds relevant evidence for all 10
questions within five results. Vector-only misses `finance-total-income` in the
top five. Versioned results:

- [Vector-only baseline](../../evaluation/baselines/vector_retrieval_v1.json)
- [Hybrid baseline](../../evaluation/baselines/hybrid_retrieval_v1.json)

The first review pass exposed incomplete relevance labels for repeated facts in
narrative and tables. Those labels were corrected before recording this
baseline; the retrieval algorithm was not changed to improve the score.

## Run

Validate locally:

```bash
python -m scripts.stage_05_retrieval.evaluate_retrieval --dry-run
```

Run against Azure and write the detailed ignored result:

```bash
python -m scripts.stage_05_retrieval.evaluate_retrieval --overwrite
```

Run the vector-only comparison:

```bash
python -m scripts.stage_05_retrieval.evaluate_retrieval \
  --mode vector \
  --overwrite
```

## Interpretation

Hybrid Recall@5 supports using up to five chunks as the initial generation
context for this corpus. Its Recall@1 shows that relying on only the first chunk
would miss three of ten questions.

This is a small, single-document baseline. Add independently reviewed
questions and more documents before treating it as production evidence.

## Student administration guide

The separate `uol-student-admin-retrieval-v1` dataset contains 10
source-verified questions across the three pages of the address-update guide.
Because the document has only three chunks, this evaluation uses Recall@1,
Recall@2, Recall@3, and MRR@3.

| Metric | Vector only | Hybrid BM25 + vector |
| --- | ---: | ---: |
| Recall@1 | 0.800 | 1.000 |
| Recall@2 | 1.000 | 1.000 |
| Recall@3 | 1.000 | 1.000 |
| MRR@3 | 0.900 | 1.000 |

Hybrid retrieval moved the relevant page-1 chunk from rank 2 to rank 1 for two
questions: selecting `Update Your Contact Details` and handling an address type
that is not initially shown.

Artifacts:

- [Reviewed dataset](../../evaluation/datasets/student_admin_retrieval_questions_v1.json)
- [Vector-only baseline](../../evaluation/baselines/student_admin_vector_retrieval_v1.json)
- [Hybrid baseline](../../evaluation/baselines/student_admin_hybrid_retrieval_v1.json)

This perfect hybrid score is a development result, not a production claim. The
corpus slice contains only three chunks, the questions are in English like the
source, and no paraphrase, typo, multilingual, or negative-query robustness set
has yet been evaluated.

Run this dataset with:

```bash
python -m scripts.stage_05_retrieval.evaluate_retrieval \
  --dataset evaluation/datasets/student_admin_retrieval_questions_v1.json \
  --mode hybrid --k 1 2 3 --vector-candidates 20 --overwrite
```

## Category-scoped multi-document evaluation

The evaluator now supports schema `1.1.0`, which defines a category and an
explicit allowlist of document IDs. This matches runtime triage more closely:
the classifier selects a category and Azure AI Search retrieves across every
approved document in that category.

Two new source-verified development datasets each contain 12 questions:

- `uol-finance-operations-retrieval-v1`: four Finance policy pages;
- `uol-digital-learning-retrieval-v1`: two student-support pages.

Both use `top=5`, 50 vector candidates, and an exact category filter.

| Dataset | Mode | Recall@1 | Recall@3 | Recall@5 | MRR@5 |
| --- | --- | ---: | ---: | ---: | ---: |
| Finance operations | Vector only | 0.917 | 1.000 | 1.000 | 0.958 |
| Finance operations | Hybrid | 0.917 | 1.000 | 1.000 | 0.958 |
| Digital learning | Vector only | 0.917 | 1.000 | 1.000 | 0.958 |
| Digital learning | Hybrid | 0.917 | 1.000 | 1.000 | 0.958 |

Unlike the annual-report and address-guide baselines, hybrid search did not
improve ranking on these two datasets: both modes produced the same first
relevant ranks. This does not show that BM25 is useless. The new corpora are
small, their documents are topically distinct, and most questions closely
match source terminology. Add paraphrases, typos, acronym variants, and harder
cross-document distractors before drawing a broader conclusion.

Artifacts:

- [Finance operations dataset](../../evaluation/datasets/finance_operations_retrieval_questions_v1.json)
- [Finance operations vector baseline](../../evaluation/baselines/finance_operations_vector_retrieval_v1.json)
- [Finance operations hybrid baseline](../../evaluation/baselines/finance_operations_hybrid_retrieval_v1.json)
- [Digital learning dataset](../../evaluation/datasets/digital_learning_retrieval_questions_v1.json)
- [Digital learning vector baseline](../../evaluation/baselines/digital_learning_vector_retrieval_v1.json)
- [Digital learning hybrid baseline](../../evaluation/baselines/digital_learning_hybrid_retrieval_v1.json)

The labels were checked against the captured public sources and deterministic
chunks. Independent Finance and Digital Education domain review remains
pending and is explicitly recorded in each dataset.
