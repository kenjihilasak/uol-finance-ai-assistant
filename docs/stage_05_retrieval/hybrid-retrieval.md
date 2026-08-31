# Hybrid retrieval

## Purpose

Stage 05 retrieves grounded evidence before answer generation. It combines two
signals because financial questions can need both exact terms and semantic
meaning.

| Signal | Input | Strength |
| --- | --- | --- |
| BM25 | Original question text | Exact names, dates, and financial terms |
| Vector | 1,536-value question embedding | Similar meaning with different wording |

Azure AI Search combines both rankings with Reciprocal Rank Fusion (RRF). Its
score orders results; it is not an answer-confidence probability. Chat
generation is kept out of this stage so retrieval quality can be inspected
independently.

## Request flow

1. Validate the question and result limits.
2. Embed the question with `text-embedding-3-small`, matching Stage 03.
3. Search `text`, `source_title`, and `institution` while querying
   `content_vector` in the same request.
4. Return the top chunks with page and source metadata.
5. Exclude `content_vector` from the selected fields.

Implementation:
[`hybrid_search.py`](../../scripts/stage_05_retrieval/hybrid_search.py).

## Current boundary

Implemented: query embedding, hybrid retrieval, optional document filter, safe
field selection, and evidence output.

Next: create a small reviewed question set and measure Recall@k/MRR before
adding `gpt-5-mini`, citations, and abstention.

## References

- [Hybrid search overview](https://learn.microsoft.com/azure/search/hybrid-search-overview)
- [Create a hybrid query](https://learn.microsoft.com/azure/search/hybrid-search-how-to-query)
