# Grounded answer generation

## Purpose

This step turns retrieved evidence into a concise answer while preserving the
boundary between retrieval and generation. It uses `gpt-5-mini` only after the
hybrid retriever returns bounded chunks.

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

Ten scope-verified unanswerable questions cover outside entities and periods,
false premises, unsupported details, personal data, and forecasts.

| Metric | Result |
| --- | ---: |
| Correct abstention rate | 1.00 |
| False answer rate | 0.00 |
| Citation-free abstention rate | 1.00 |

The run used 15,492 input, 1,291 output, and 16,783 total chat tokens. See the
[negative dataset](../../evaluation/datasets/abstention_questions_v1.json) and
[versioned baseline](../../evaluation/baselines/abstention_v1.json).

The first draft incorrectly labelled a Moody's rating question as unanswerable;
page 83 did contain the answer. The label was corrected to a Fitch question and
the full dataset rerun. This review is part of evaluation quality, not a model
failure.

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
