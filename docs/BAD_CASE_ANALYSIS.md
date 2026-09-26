# Recall Bad Case Analysis

## Scope

This analysis uses 45 manually labelled questions grounded in the imported eight-page AI Product Manager PDF:

- 35 answerable questions with expected page labels;
- 10 unanswerable questions that the system should refuse;
- V0 keyword retrieval, V1 embedding retrieval, and V2 hybrid retrieval plus reranking.

The purpose is not to claim universal RAG quality. It is to document what failed on the current corpus, why it failed, and which product or architecture decision followed.

## Final result

| Version | Hit@1 | Hit@3 | Hit@5 | MRR@5 | Abstention accuracy | False refusal | Mean latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| V0 Keyword | 82.9% | 97.1% | 97.1% | 0.900 | 80.0% | 14.3% | 1 ms |
| V1 Embedding | 77.1% | 94.3% | 100.0% | 0.867 | 80.0% | 14.3% | 93 ms |
| V2 Hybrid + Reranker | 85.7% | 100.0% | 100.0% | 0.919 | 100.0% | 0.0% | 9.5 s |

## Case 1 — Keyword retrieval missed a concept definition

**Question:** `q29 向量化在AI系统里有什么作用？`

**Expected page:** 7  
**V0 Top 5 pages:** 3, 4, 5, 5, 3

### Cause

The deterministic tokenizer is deliberately lightweight. Chinese bigram overlap over-weighted generic words such as “能力”“系统”“产品”, while the definition on page 7 used “向量”“数字”“距离”“相似度”. Lexical retrieval could not connect the user's phrasing “有什么作用” with the semantic description.

### Decision

Add Qwen3 Embedding as a recall channel. V1 raised Hit@5 from 97.1% to 100%, ensuring that every labelled answerable question had a correct page in the candidate set.

### Trade-off

Embedding did not improve first-place ranking by itself: Hit@1 fell from 82.9% to 77.1%. Semantic similarity increased recall but also brought broad, topically related passages to the top.

## Case 2 — Embedding retrieved related but non-answering passages

Examples included:

- `q03` asking for the three core tasks, where page 4 was ranked above page 1;
- `q20` asking about the product/model dual loop, where pages 7 and 6 ranked above page 4;
- `q29` asking about vectorisation, where page 6 ranked above page 7.

### Cause

Dense retrieval optimises semantic proximity, not whether a passage directly answers the question. In a single-topic document, many chunks are semantically close even when they do not contain the required fact.

### Decision

Merge keyword and vector candidates, then run a second-stage listwise reranker. Retrieval scores remain part of the final score so the model cannot freely discard strong exact evidence.

## Case 3 — The first generative reranker made ranking worse

### Initial result

The first V2 implementation passed up to 20 long candidates to `qwen3:latest` and asked it to assign absolute relevance scores. One question took about 55 seconds, and the resulting ranking sometimes placed unrelated passages first.

### Cause

- excessive candidate context;
- absolute scores were inconsistent between calls;
- a general chat model was doing a ranking task;
- model judgement completely replaced retrieval evidence.

### Decision

- use `qwen3:0.6b` for the ranking stage;
- pre-filter to ten hybrid candidates;
- truncate each candidate to 600 characters;
- request only a relative ID ordering;
- weight the final score 80% retrieval evidence and 20% model ordering.

This reduced warm ranking latency to roughly 3–4 seconds and raised final Hit@1 above both single-channel versions.

## Case 4 — Small reranker accepted every question

### Initial result

The 0.6B model was effective enough for relative ordering but returned `answerable=true` for all ten unanswerable questions when ranking and sufficiency were combined in one prompt. Abstention accuracy was therefore 0%.

### Cause

Ranking asks “which candidate is best”, while sufficiency asks “is any candidate good enough”. Combining the two encourages the model to select the least-bad passage and then treat it as evidence.

### Decision

Separate responsibilities:

1. `qwen3:0.6b` ranks candidates;
2. `qwen3:latest` inspects only the top three short passages and performs strict evidence-sufficiency classification;
3. answer generation runs only when evidence passes the gate.

This produced 100% abstention accuracy, but the first strict version incorrectly refused seven answerable questions.

## Case 5 — Strict sufficiency created false refusals

The seven incorrectly refused questions all had a top vector similarity of at least 0.586. Every unanswerable question had a top vector similarity of at most 0.572.

### Decision

Introduce a configurable semantic evidence floor of `0.58`. A strong semantic match can override an overly conservative LLM rejection. The final evaluation achieved:

- 100% abstention accuracy;
- 0% false-refusal rate;
- 100% Hit@3 and Hit@5.

### Important limitation

The `0.58` boundary was calibrated on the same 45-question, single-document dataset. It is a product calibration result, not a universal threshold. Before production use it must be validated on:

- more documents and domains;
- paraphrased questions written by people outside the project;
- adversarial near-match questions;
- scanned PDFs with OCR noise.

## Product implications

1. **Do not present Embedding as an automatic quality upgrade.** It improved candidate coverage but reduced Hit@1 alone.
2. **Separate recall, ranking, sufficiency, and generation metrics.** A fluent answer cannot compensate for wrong evidence.
3. **Expose the waiting stages in the UI.** V2 costs about 9.5 seconds before answer generation, so the interface now shows recall, reranking, evidence verification, and generation states.
4. **Prefer trustworthy refusal over fast unsupported answers.** The current local version accepts latency as a deliberate trade-off.
5. **Keep evaluation reproducible.** Questions, page labels, raw hits, latency, and the evaluation runner are checked into the repository.

## Next evaluation iteration

- Expand to at least five documents and 100 questions.
- Split calibration and held-out test sets before adjusting thresholds.
- Add claim-level citation accuracy and answer completeness labels.
- Measure cold-start and warm-start latency separately.
- Compare the current generative reranker with a dedicated cross-encoder reranker.
