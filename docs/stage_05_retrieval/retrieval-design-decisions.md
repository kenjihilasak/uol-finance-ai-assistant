# Retrieval design decisions

## Purpose

This note explains why the runtime retrieval pipeline uses four complementary
controls:

```text
Original enquiry ──> BM25 keyword ranking ──┐
                                            ├─> RRF ─> top 5 chunks
Query embedding ───> HNSW vector ranking ──┘
                         ^
                         └─ exact category filter
```

Retrieval is executed by Azure AI Search. It is separate from answer
generation: its job is to select evidence, not to write the response.

## Inputs sent to Azure AI Search

For an approved enquiry, FastAPI sends one hybrid search request containing:

| Input | Example | Purpose |
| --- | --- | --- |
| `search_text` | `Student cannot submit coursework in Minerva` | BM25 keyword search |
| `query_vector` | 1,536 floats returned by `text-embedding-3-small` | HNSW similarity search |
| `filter` | `category eq 'digital_learning'` | Restrict retrieval to the classified domain |
| `vector_candidates` | `50` | Candidate neighbours considered by vector search |
| `top` | `5` | Final chunks returned after fusion |

The original enquiry supplies both retrieval signals: its text is used
directly by BM25 and its embedding is used by vector search. The category is
produced earlier by the enquiry classifier; the browser does not choose it.

## Why BM25

BM25 is a lexical ranking method. It rewards query terms that occur in a
document, gives more weight to relatively rare terms, and controls the effect
of repeated words and document length.

A simplified view is:

```text
BM25 score = sum of each query term's rarity and normalised term frequency
```

It is valuable here because university enquiries contain exact operational
language such as `Minerva`, `receipt`, `mileage`, dates, policy names and
financial line items. Embedding similarity can understand the topic while
still ranking a chunk with the exact required term too low.

The implementation searches these fields:

```python
SEARCH_FIELDS = ["text", "source_title", "institution"]
```

BM25 alone was not selected because vocabulary mismatch remains possible. For
example, a source may say `supporting evidence` while the enquiry says
`replacement for a lost receipt`.

## Why vector similarity and HNSW

`text-embedding-3-small` maps the enquiry and every stored chunk into the same
1,536-dimensional vector space. Semantically related text should be closer in
that space even when it uses different words.

Azure AI Search stores each document embedding in `content_vector`. Runtime
queries compare the temporary query vector with those stored vectors.

The index uses HNSW (Hierarchical Navigable Small World), an approximate
nearest-neighbour algorithm. HNSW builds a navigable multi-layer graph over
the vectors. At query time it traverses the graph to find strong candidates
without comparing the query with every vector.

HNSW was chosen because it provides a practical latency/recall trade-off for
interactive search and is natively managed by Azure AI Search. Approximate
search can theoretically miss a true nearest neighbour, so retrieval quality
must be evaluated rather than assumed.

Vector-only search was not selected because semantic similarity can underweight
exact identifiers, figures and policy terminology. The project's reviewed
baseline also ranked relevant evidence earlier with hybrid retrieval.

## Why Reciprocal Rank Fusion

BM25 scores and vector-similarity scores are not directly comparable. RRF
combines their *ranks* instead of trying to normalise the raw scores.

For a chunk `d`, the conceptual fusion score is:

```text
RRF(d) = sum(1 / (rank(d, list) + k))
```

`k` is an RRF smoothing constant; it is unrelated to the 50 vector candidates
or the five final results. A chunk receives one contribution for each ranked
list in which it appears. A chunk near the top of both lists usually outranks a
chunk supported by only one signal.

Example with a simplified `k = 60`:

| Chunk | BM25 rank | Vector rank | Fused contribution |
| --- | ---: | ---: | ---: |
| A | 1 | 3 | `1/61 + 1/63` |
| B | 2 | absent | `1/62` |
| C | 5 | 1 | `1/65 + 1/61` |

Chunk C can move above B because two independent retrieval signals support it.
Azure AI Search performs this fusion inside the hybrid request.

RRF was selected because it is simple, robust to incompatible score scales,
and available as a managed Azure operation. It does not make the resulting
`@search.score` a confidence probability.

## Why the category filter

The classification stage assigns one answerable category:

```text
finance
finance_operations
student_admin
digital_learning
```

FastAPI converts it to an escaped OData filter, for example:

```text
category eq 'digital_learning'
```

The filter prevents otherwise similar chunks from the wrong operational domain
from entering the final ranking. It improves precision and enforces a corpus
boundary: a Minerva enquiry should not be grounded in an annual report or an
expenses policy.

This is a deterministic retrieval constraint, not an instruction to the
generation model. Sensitive and unsupported categories stop before retrieval,
so they do not receive a category-filtered RAG answer.

The trade-off is classifier dependency. A wrong category can exclude the right
evidence completely. This is why triage classification and retrieval are
evaluated separately and why uncertain enquiries request clarification or
manual review.

## Why 50 candidates and five returned chunks

The deployed API uses:

```text
vector candidates = 50
final results = 5
```

Fifty candidates give the vector branch a wider pool before ranking is fused.
Only the top five fused chunks are returned and prepared as evidence. Limiting
the final context reduces model input size, latency, cost and the risk of
irrelevant context distracting generation.

Five is an evidence-based development setting, not a universal optimum. On the
reviewed finance dataset, hybrid Recall@5 was `1.000`, while Recall@1 was
`0.700`. The small evaluation supports using more than one chunk but must be
expanded before making a production claim.

## Evidence from the project

The reviewed finance baseline used ten questions with the same `top=5` and 50
vector candidates:

| Metric | Vector only | Hybrid BM25 + vector |
| --- | ---: | ---: |
| Recall@1 | 0.500 | 0.700 |
| Recall@3 | 0.900 | 0.900 |
| Recall@5 | 0.900 | 1.000 |
| MRR@5 | 0.683 | 0.825 |

The result supports the hybrid choice for this development corpus: it improved
early ranking and recovered relevant evidence for all ten reviewed questions
within the first five results. On the newer finance-operations and
digital-learning datasets, however, hybrid and vector-only retrieval tied at
`MRR@5 = 0.958`. Hybrid retrieval is therefore retained as a robust combined
default, not claimed as universally superior. See
[retrieval evaluation](./retrieval-evaluation.md) for dataset-specific results
and limitations.

## Alternatives considered

| Option | Why it is not the current default |
| --- | --- |
| BM25 only | Weak when enquiry and source use different vocabulary |
| Vector only | Can underweight exact names, figures and policy terms; performed worse in the baseline |
| Exhaustive vector search | Higher compute cost; unnecessary for the current interactive managed-search design |
| Application-side fusion | More code and network operations when Azure already provides managed hybrid fusion |
| Semantic Ranker | Separate Azure feature and cost/availability decision; not required for the measured baseline |
| Let the LLM choose passages | Less deterministic, harder to evaluate, and mixes retrieval with generation |

## Implementation map

| Concern | Location |
| --- | --- |
| Query validation and defaults | `scripts/stage_05_retrieval/hybrid_search.py` |
| BM25 fields | `SEARCH_FIELDS` in `hybrid_search.py` |
| HNSW query | `VectorizedQuery` in `hybrid_search.py` |
| Category/document filter | `search_filter()` in `hybrid_search.py` |
| Hybrid Azure request | `hybrid_search()` in `hybrid_search.py` |
| HNSW index schema | `scripts/stage_04_search_index/create_index.py` |
| Runtime `top=5`, candidates `50` | `scripts/stage_06_triage/triage_enquiry.py` |
| Measured comparison | `docs/stage_05_retrieval/retrieval-evaluation.md` |

The stored vectors are deliberately excluded from result fields. FastAPI needs
the evidence text and provenance, not 1,536 floats per returned chunk.

## Study checklist

After reading this note, you should be able to explain:

1. Why exact lexical matches and semantic similarity are different signals.
2. Why HNSW is approximate and why its quality must be measured.
3. Why RRF combines ranks instead of raw BM25 and vector scores.
4. Why a category filter is both a relevance and routing control.
5. Why 50 candidates does not mean 50 chunks are sent to the LLM.
6. Why Azure AI Search is both the hybrid search engine and managed vector
   store in this project.

## References

- [Azure hybrid search overview](https://learn.microsoft.com/azure/search/hybrid-search-overview)
- [Azure RRF ranking](https://learn.microsoft.com/azure/search/hybrid-search-ranking)
- [Azure vector search overview](https://learn.microsoft.com/azure/search/vector-search-overview)
- [Azure HNSW configuration](https://learn.microsoft.com/azure/search/vector-search-how-to-create-index)
- [Azure relevance scoring and BM25](https://learn.microsoft.com/azure/search/index-similarity-and-scoring)
