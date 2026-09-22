# Retrieval evaluation

This report compares vector-only and hybrid retrieval across the four
answerable categories. Versioned outputs are stored in `evaluation/baselines/`.

## Executive summary

| Evaluation layer | Coverage | Main result |
| --- | ---: | --- |
| Retrieval | 44 questions, 4 categories | Hybrid Recall@1: **88.6%** |
| Retrieval | Same 44 questions | Vector-only Recall@1: **79.5%** |
| Ranking | Same 44 questions | Hybrid MRR@5: **0.938** |

Hybrid retrieval improved the overall first-result hit rate by **9.1 percentage
points**. The gain came from the annual-report and student-administration
datasets; hybrid and vector-only tied on the two newer categories. Hybrid is
therefore the selected default, but the evidence does not claim that it is
always superior.

## Retrieval results

Recall@1 is the percentage of questions for which the first result contains
relevant evidence. MRR measures how early the first relevant chunk appears.

All runs used the same Azure AI Search index and
`text-embedding-3-small`. The top-five evaluations used 50 vector candidates
and an exact category filter.

| Category | Questions | Vector Recall@1 | Hybrid Recall@1 | Hybrid final recall | Hybrid MRR |
| --- | ---: | ---: | ---: | ---: | ---: |
| Finance report | 10 | 0.500 | **0.700** | Recall@5: 1.000 | MRR@5: 0.825 |
| Student administration | 10 | 0.800 | **1.000** | Recall@3: 1.000 | MRR@3: 1.000 |
| Finance operations | 12 | 0.917 | **0.917** | Recall@5: 1.000 | MRR@5: 0.958 |
| Digital learning | 12 | 0.917 | **0.917** | Recall@5: 1.000 | MRR@5: 0.958 |
| **Weighted overall** | **44** | **0.795** | **0.886** | **1.000** | **MRR@5: 0.938** |

The weighted overall row is calculated across questions, not by averaging the
four category percentages. Student administration was originally reported as
MRR@3 because its corpus has only three chunks. Its MRR@5 is therefore
identical: ranks four and five do not exist. This allows a comparable weighted
MRR@5 across all 44 questions. Vector-only MRR@5 is 0.883; hybrid MRR@5 is
0.938.

## Conclusions and limits

- Hybrid retrieval is the best current default across the full corpus.
- Top-five retrieval found relevant evidence for every evaluated question.
- The datasets are small and source-verified, but independent Finance and
  Digital Education review remains pending.
- More paraphrases, typos, acronyms, multilingual questions and hard
  cross-document distractors are needed before production use.

## Evidence

- [Retrieval datasets](../../evaluation/datasets/)
- [Versioned baselines](../../evaluation/baselines/)
- [Independent-review template](../../evaluation/reviews/independent_domain_review.md)
- [Retrieval design decisions](retrieval-design-decisions.md)
- [Triage evaluation](../stage_06_triage/triage-evaluation.md)

## Reproduce

```bash
# Validate a retrieval dataset locally
python -m scripts.stage_05_retrieval.evaluate_retrieval --dry-run

# Run a category-scoped hybrid evaluation against Azure
python -m scripts.stage_05_retrieval.evaluate_retrieval \
  --dataset evaluation/datasets/finance_operations_retrieval_questions_v1.json \
  --mode hybrid --k 1 3 5 --vector-candidates 50 --overwrite
```
