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
