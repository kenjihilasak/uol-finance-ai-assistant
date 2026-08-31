# Grounded answer generation

## Purpose

This step turns retrieved evidence into a concise answer while preserving the
boundary between retrieval and generation. It uses `gpt-5-mini` only after the
hybrid retriever returns up to five chunks.

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
- Every citation ID must identify a retrieved chunk.
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

## Ten-question positive evaluation

The full reviewed positive set was executed with one embedding batch and 10
`gpt-5-mini` responses.

| Metric | Result |
| --- | ---: |
| Answered rate | 1.00 |
| Relevant context hit rate | 1.00 |
| Relevant citation hit rate | 1.00 |
| Citation precision | 0.85 |
| Manually reviewed answer correctness | 1.00 |

All 10 answers matched their concise references during development review.
Three answers included additional retrieved citations not labelled as relevant,
which reduced macro-averaged citation precision without changing answer
correctness.

Token usage for the run was 16,141 input, 1,844 output, and 17,985 total tokens.
The concise versioned result is
[`generation_positive_v1.json`](../../evaluation/baselines/generation_positive_v1.json).
Detailed answers remain in ignored `data/evaluation/` for local review.

Run the positive evaluation:

```bash
python -m scripts.stage_05_retrieval.evaluate_generation --overwrite
```

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
