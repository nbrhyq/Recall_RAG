# RAG evaluation plan

Recall separates retrieval quality from answer quality. A fluent answer does not compensate for unsupported evidence.

## Offline set

Create 30–50 questions across at least three topics. For each question, label:

- supporting document IDs and page numbers;
- required facts;
- whether the library contains enough evidence;
- misleading but semantically similar document passages.

## Metrics

| Metric | Definition | MVP target |
|---|---|---:|
| Retrieval Hit Rate@5 | Questions where at least one labelled source is in the top five | ≥ 85% |
| Citation Accuracy | Citations that directly support their attached claim | ≥ 90% |
| Answer Relevance | Human 1–5 rating for whether the answer resolves the question | ≥ 4.0 |
| Source Coverage | Labelled supporting sources represented in the answer | ≥ 75% |
| Abstention Precision | Unanswerable questions correctly refused | ≥ 90% |

## Test cases included in the MVP

- Mixed Chinese/English professional terms such as `RAG` and `reranker` survive tokenisation.
- Relevant evidence ranks above unrelated content.
- Time ranges survive ingestion and chunk construction.
- Questions without sufficient overlap receive an explicit insufficiency response.

## Feedback instrumentation roadmap

Answer feedback should capture helpful/not helpful, citation incorrect, missing source, and answer unsupported as separate signals. A single thumbs-down cannot diagnose the RAG stage that failed.

## Reproducible implementation

- Question set: `apps/api/evaluation/questions.json`
- Runner: `apps/api/evaluation/run_retrieval_eval.py`
- Raw results: `apps/api/evaluation/results.json`
- Final comparison: `docs/EVALUATION_RESULTS.md`
- Failure analysis: `docs/BAD_CASE_ANALYSIS.md`
