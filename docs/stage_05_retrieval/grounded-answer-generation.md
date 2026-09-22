# Grounded answer generation

## Purpose

This step turns retrieved evidence into a concise answer while preserving the
boundary between retrieval and generation. It uses `gpt-5-mini` only after the
hybrid retriever returns bounded chunks.

## Evaluation snapshot

| Measure | Result |
| --- | ---: |
| Answerable questions | 44 across 4 categories |
| Development-reviewed correct | 44/44 |
| Relevant citation hit | 100% |
| Citation precision | 93.6% |
| Correct abstentions | 20/20 across 4 categories |
| False answers on unanswerable questions | 0 |

`20/20 correct abstentions` measures whether the answer layer refuses when the
category-filtered approved evidence is insufficient. It is not a
retrieval-ranking metric like Recall@k or MRR. A presentation may place it
beside retrieval under a broader heading such as **RAG performance**.

## Flow

```text
question
  -> query embedding
  -> hybrid top 5
  -> bounded evidence S1...S5
  -> gpt-5-mini structured output
  -> citation and abstention validation
  -> answer or abstention
```

## Output contract

```json
{
  "status": "answered | abstained",
  "answer": "concise text",
  "citation_ids": ["S1"]
}
```

Rules enforced in code:

- `answered` requires at least one citation.
- The response schema permits only the supplied `S1...Sn` citation IDs.
- A second validator rejects any citation ID that does not identify retrieved evidence.
- `abstained` must have no citations.
- Evidence is bounded to five chunks and 15,000 characters.
- Retrieved text is labelled as untrusted data, not instructions.
- Vectors and search scores are not sent to the chat model.

Structural citation validation prevents invented source IDs. It does not prove
that every answer statement is supported by the cited text; generation
evaluation must measure groundedness and citation correctness separately.

## Run

```bash
python -m scripts.stage_05_retrieval.generate_grounded_answer \
  --query "What was the University's total income in 2024/25?"
```

Dry run:

```bash
python -m scripts.stage_05_retrieval.generate_grounded_answer \
  --query "What was the University's total income in 2024/25?" \
  --dry-run
```

## Positive generation evaluation

The same grounded-generation contract was evaluated across all four answerable
categories.

| Category | Questions | Answered | Relevant citation hit | Citation precision | Development-reviewed correct |
| --- | ---: | ---: | ---: | ---: | ---: |
| Finance report | 10 | 1.000 | 1.000 | 0.850 | 10/10 |
| Student administration | 10 | 1.000 | 1.000 | 1.000 | 10/10 |
| Finance operations | 12 | 1.000 | 1.000 | 0.889 | 12/12 |
| Digital learning | 12 | 1.000 | 1.000 | 1.000 | 12/12 |
| **Overall** | **44** | **1.000** | **1.000** | **0.936** | **44/44** |

Citation precision is macro-averaged across questions. It falls below 1.0 when
an answer cites additional retrieved chunks that were not labelled relevant,
even when the answer remains correct and supported.

The four accepted runs used 59,963 input tokens, 7,746 output tokens and 67,709
total tokens. Versioned baselines:

- [Finance report](../../evaluation/baselines/generation_positive_v1.json)
- [Student administration](../../evaluation/baselines/student_admin_generation_positive_v1.json)
- [Finance operations](../../evaluation/baselines/finance_operations_generation_positive_v1.json)
- [Digital learning](../../evaluation/baselines/digital_learning_generation_positive_v1.json)

Detailed responses remain in ignored `data/evaluation/` for local review.

## Abstention evaluation

Twenty scope-verified unanswerable questions cover all four RAG categories,
with five cases per category. They test false premises, unsupported details,
personal data, credentials, future events and forecasts.

| Metric | Result |
| --- | ---: |
| Correct abstention rate | 1.00 |
| False answer rate | 0.00 |
| Citation-free abstention rate | 1.00 |

In presentation form: **20/20 correct abstentions across four categories and 0
false answers**.

The run used 19,203 input, 1,863 output, and 21,066 total chat tokens. See the
[four-category dataset](../../evaluation/datasets/abstention_questions_v2.json)
and [versioned baseline](../../evaluation/baselines/abstention_v2.json). The
original finance-only v1 artifacts remain as historical evidence.

```bash
python -m scripts.stage_05_retrieval.evaluate_abstention --overwrite
```

Independent domain review is still required before production-quality claims.

Run any positive dataset with:

```bash
python -m scripts.stage_05_retrieval.evaluate_generation \
  --dataset evaluation/datasets/digital_learning_retrieval_questions_v1.json \
  --output data/evaluation/digital_learning_generation_positive_v1.results.json \
  --overwrite
```
