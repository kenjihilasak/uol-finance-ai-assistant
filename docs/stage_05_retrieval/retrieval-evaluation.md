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
- MRR@5: mean reciprocal rank of the first relevant chunk in the top five; a
  miss contributes zero.

These metrics evaluate retrieval only. They do not measure answer correctness,
groundedness, citations, or abstention.

## Baseline

Configuration: hybrid BM25 + vector search, `top=5`, 50 vector candidates,
`text-embedding-3-small`, index `uol-finance-chunks-v1`.

| Metric | Result |
| --- | ---: |
| Recall@1 | 0.700 |
| Recall@3 | 0.900 |
| Recall@5 | 1.000 |
| MRR@5 | 0.825 |

Seven questions placed a relevant chunk first, two placed it second, and one
placed it fourth. The versioned result is
[`hybrid_retrieval_v1.json`](../../evaluation/baselines/hybrid_retrieval_v1.json).

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

## Interpretation

Recall@5 supports using up to five chunks as the initial generation context for
this corpus. Recall@1 shows that relying on only the first chunk would miss
three of ten questions.

This is a small, single-document baseline. Add independently reviewed
questions and more documents before treating it as production evidence.
