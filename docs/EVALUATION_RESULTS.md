# Recall retrieval evaluation results

Dataset: 45 questions (35 answerable, 10 unanswerable).

| Version | Retrieval | Hit@1 | Hit@3 | Hit@5 | MRR@5 | Abstention | Mean latency |
|---|---|---:|---:|---:|---:|---:|---:|
| V0 | Keyword only | 82.9% | 97.1% | 97.1% | 0.900 | 80.0% | 1 ms |
| V1 | Embedding only | 77.1% | 94.3% | 100.0% | 0.867 | 80.0% | 93 ms |
| V2 | Keyword + embedding + Qwen3 reranker | 85.7% | 100.0% | 100.0% | 0.919 | 100.0% | 9505 ms |

## Bad cases

### v0_keyword

- `q29` 向量化在AI系统里有什么作用？ — expected [7], retrieved [3, 4, 5, 5, 3]

### v1_embedding

- No answerable Hit@5 failures.

### v2_hybrid_rerank

- No answerable Hit@5 failures.

## Method

- V0 ranks SQLite chunks with deterministic mixed Chinese/English keyword relevance.
- V1 retrieves Qwen3 Embedding vectors from local Qdrant.
- V2 merges both candidate sets, applies a Qwen3 0.6B listwise reranker with retrieval-score safeguards, then uses Qwen3 8B for evidence sufficiency.
- A calibrated vector-similarity floor of 0.58 can override an overly conservative sufficiency rejection.
- Page-level relevance labels were authored from the imported eight-page source PDF.
- Latency is wall-clock time on the evaluation machine and should be compared directionally.
