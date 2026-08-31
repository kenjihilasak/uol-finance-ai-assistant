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

## Verified smoke tests

An in-scope question returned £999m, 5% lower than 2023/24, citing page 75.
An out-of-scope question about Apple revenue returned `abstained` with no
citations.

These two checks verify the end-to-end contract, not overall generation
quality. The next evaluation should include all reviewed positive questions and
several deliberately unanswerable questions.
