# Chunking strategy

Stage 02 converts page text into retrieval units. The goal is not to create the
fewest chunks; it is to keep each chunk understandable, traceable to one page,
and small enough for precise retrieval.

## Why the first algorithm was simple

Version 1 used 1,800-character windows with 200 characters of overlap. It was a
useful baseline because it was deterministic, dependency-free, page-bounded,
and easy to verify. Those properties matter for citations and regression tests.

Its weakness was semantic: the next window started a fixed number of characters
back, so it could begin inside a sentence or table row. It also knew nothing
about paragraphs, headings, or document structure.

## Five approaches

| Approach | Example behaviour | Strength | Main risk |
| --- | --- | --- | --- |
| Fixed window | Split every N characters or tokens. | Fast baseline. | Cuts ideas at arbitrary positions. |
| Sentence-aware | Keep `Research income also grew.` intact. | Readable evidence. | A sentence can be too long or lack its heading. |
| Recursive | Try page, paragraph, sentence, then word boundaries. | Predictable with better coherence. | Still depends on extracted text order. |
| Layout-aware | Keep a financial table, its heading, and row labels together. | Best fit for reports. | Requires a layout parser and more cost. |
| Semantic or hierarchical | Retrieve a focused child chunk, then expand to its section or parent. | Balances precision and context. | More complex indexing and evaluation. |

NotebookLM is a useful product comparison, but its public help explains source
grounding and inline citations rather than its internal splitting algorithm.
This project therefore does not claim to reproduce NotebookLM. The comparable
public Google Cloud patterns are token windows and layout parsing with heading,
table, and hierarchy awareness.

References:

- [NotebookLM grounding and citations](https://support.google.com/notebooklm/answer/16164461?hl=en)
- [Google Cloud RAG transformations](https://cloud.google.com/vertex-ai/generative-ai/docs/fine-tune-rag-transformations)
- [Google Document AI layout-aware chunking](https://docs.cloud.google.com/document-ai/docs/layout-parse-chunk)
- [Azure AI Search chunking guidance](https://learn.microsoft.com/azure/search/vector-search-how-to-chunk-documents)
- [Azure Document Intelligence for RAG](https://learn.microsoft.com/azure/ai-services/document-intelligence/concept-retrieval-augumented-generation)

## Implemented algorithm: version 2

The current local algorithm is recursive and page-bounded:

1. Keep physical PDF pages as citation boundaries.
2. Find paragraph boundaries.
3. Split paragraphs at sentence boundaries.
4. Split only oversized sentences at word boundaries.
5. Pack complete units toward 1,200 characters, with a hard limit of 1,800.
6. Reuse complete units for up to 200 characters of overlap.
7. Merge tails below 300 characters when the result stays within the limit.

Raw `text` remains suitable for display and citation. `embedding_text` adds the
document title, institution, and page before vectorisation so a short chunk does
not lose all document context.

Characters are used for this local baseline to avoid a tokenizer dependency.
Google Cloud and Azure also support token-based sizing; changing units should be
driven by retrieval evaluation, not by copying a default.

## Result on the current annual report

| Measure | Version 1 | Version 2 |
| --- | ---: | ---: |
| Chunks | 462 | 490 |
| Average characters | 1,448 | 1,260 |
| Chunks below 300 characters | 22 | 25 |
| Later chunks starting lowercase | 146/302 | 23/330 |

The lowercase measure is a heuristic, not a quality score, but it exposes many
mid-sentence starts in version 1. Version 2 creates more focused chunks and far
fewer such starts. Short whole pages, section dividers, and extracted table
fragments still exist because chunks never cross page boundaries.

## Known limit and next experiment

`pypdf` layout extraction can flatten columns and tables into the wrong reading
order. A chunker cannot reconstruct structure that extraction already lost.
For this financial report, the next meaningful comparison is:

1. Keep version 2 as the transparent baseline.
2. Extract the same pages with Azure Document Intelligence Layout.
3. Preserve Markdown headings and tables.
4. Build identical retrieval questions for both variants.
5. Compare Recall@k, MRR, citation-page accuracy, latency, and cost.

Only promote the layout-aware variant if the evaluation improves.
