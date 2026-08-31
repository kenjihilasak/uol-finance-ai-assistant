# Stage 05: hybrid retrieval

This stage embeds one user question and sends both inputs to Azure AI Search:

- `search_text`: lexical BM25 matching over `text`, title, and institution.
- `content_vector`: semantic nearest-neighbour matching over the same embedding
  space used in Stage 03.

Azure AI Search fuses the two ranked result lists with Reciprocal Rank Fusion
(RRF). The command returns evidence chunks and provenance only; it does not
call the chat model. The resulting score is a ranking signal, not a probability
or a validated confidence threshold.

## Run

From the repository root:

```bash
python -m scripts.stage_05_retrieval.hybrid_search \
  --query "What was the University's total income in 2025?" \
  --top 5 \
  --vector-candidates 50
```

Validate configuration without contacting Azure:

```bash
python -m scripts.stage_05_retrieval.hybrid_search \
  --query "What was the University's total income in 2025?" \
  --dry-run
```

`--top` controls returned evidence. `--vector-candidates` controls how many
vector neighbours participate in rank fusion and must be at least `top`.
`--document-id` optionally restricts retrieval to one indexed document.

The query uses Entra ID and `text-embedding-3-small`. Its output deliberately
excludes `content_vector`, so 1,536-float vectors never enter logs or prompts.

## Evaluate

Validate the tracked question set without contacting Azure:

```bash
python -m scripts.stage_05_retrieval.evaluate_retrieval --dry-run
```

Run the hybrid baseline and calculate Recall@1/3/5 and MRR@5:

```bash
python -m scripts.stage_05_retrieval.evaluate_retrieval --overwrite
```

Compare vector-only retrieval using the same dataset and parameters:

```bash
python -m scripts.stage_05_retrieval.evaluate_retrieval \
  --mode vector \
  --overwrite
```

Detailed results go to ignored `data/evaluation/`; the reviewed dataset and
concise baseline are versioned under `evaluation/`.

## Generate a grounded answer

After validating retrieval, generate an answer from at most five chunks:

```bash
python -m scripts.stage_05_retrieval.generate_grounded_answer \
  --query "What was the University's total income in 2024/25?"
```

The model must return `answered` with valid retrieved source IDs or `abstained`
without citations. This is a CLI learning boundary; the HTTP API comes later.
