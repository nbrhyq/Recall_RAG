"""Reproducible V0/V1/V2 retrieval evaluation for the Recall case study."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import connection, initialise, row_dict
from app.ollama import rerank
from app.rag import relevance
from app.vector_store import semantic_search


HERE = Path(__file__).resolve().parent
QUESTIONS_PATH = HERE / "questions.json"
RESULTS_PATH = HERE / "results.json"
REPORT_PATH = HERE.parent.parent.parent / "docs" / "EVALUATION_RESULTS.md"

THRESHOLDS = {"v0_keyword": 0.25, "v1_embedding": 0.55, "v2_hybrid_rerank": 0.25}


def load_chunks() -> list[dict]:
    with connection() as conn:
        return [
            row_dict(row)
            for row in conn.execute(
                """
                SELECT c.id, c.video_id AS document_id, c.text, c.page_number,
                       c.start_time, c.end_time, v.title, v.author, v.url,
                       v.source_type, v.file_name
                FROM chunks c JOIN videos v ON v.id = c.video_id
                WHERE v.source_type != 'video'
                """
            )
        ]


def keyword_search(question: str, chunks: list[dict], limit: int = 20) -> list[dict]:
    ranked = [{**chunk, "keyword_score": relevance(question, chunk["text"])} for chunk in chunks]
    ranked.sort(key=lambda item: item["keyword_score"], reverse=True)
    return [{**item, "score": item["keyword_score"]} for item in ranked[:limit]]


def vector_search(question: str, limit: int = 20) -> list[dict]:
    return [{**item, "score": item["vector_score"]} for item in semantic_search(question, limit=limit)]


def hybrid_rerank(question: str, chunks: list[dict], limit: int = 5) -> list[dict]:
    keyword = keyword_search(question, chunks, 20)
    vector = vector_search(question, 20)
    merged = {item["id"]: item for item in vector}
    for item in keyword:
        merged[item["id"]] = {**merged.get(item["id"], {}), **item}
    return rerank(question, list(merged.values()), limit=limit)


def serialise_hits(hits: list[dict]) -> list[dict]:
    return [
        {
            "id": hit["id"],
            "page_number": hit.get("page_number"),
            "score": round(float(hit.get("score", 0)), 6),
            "text": hit["text"][:240],
        }
        for hit in hits[:5]
    ]


def metrics(rows: list[dict], version: str) -> dict:
    answerable = [row for row in rows if row["answerable"]]
    unanswerable = [row for row in rows if not row["answerable"]]
    reciprocal_ranks: list[float] = []
    hits = {1: 0, 3: 0, 5: 0}
    for row in answerable:
        expected = set(row["pages"])
        ranks = [index + 1 for index, hit in enumerate(row["hits"]) if hit["page_number"] in expected]
        rank = min(ranks, default=0)
        reciprocal_ranks.append(1 / rank if rank else 0)
        for k in hits:
            hits[k] += int(bool(rank and rank <= k))
    threshold = THRESHOLDS[version]
    refused = sum(not row["hits"] or row["hits"][0]["score"] < threshold for row in unanswerable)
    false_refusals = sum(not row["hits"] or row["hits"][0]["score"] < threshold for row in answerable)
    return {
        "questions": len(rows),
        "answerable": len(answerable),
        "hit_rate_at_1": round(hits[1] / len(answerable), 3),
        "hit_rate_at_3": round(hits[3] / len(answerable), 3),
        "hit_rate_at_5": round(hits[5] / len(answerable), 3),
        "mrr_at_5": round(statistics.mean(reciprocal_ranks), 3),
        "abstention_accuracy": round(refused / len(unanswerable), 3) if unanswerable else 0.0,
        "false_refusal_rate": round(false_refusals / len(answerable), 3),
        "mean_latency_ms": round(statistics.mean(row["latency_ms"] for row in rows)),
        "threshold": threshold,
    }


def write_report(payload: dict) -> None:
    versions = payload["versions"]
    lines = [
        "# Recall retrieval evaluation results",
        "",
        f"Dataset: {payload['dataset_size']} questions ({payload['answerable']} answerable, {payload['unanswerable']} unanswerable).",
        "",
        "| Version | Retrieval | Hit@1 | Hit@3 | Hit@5 | MRR@5 | Abstention | Mean latency |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    labels = {
        "v0_keyword": "Keyword only",
        "v1_embedding": "Embedding only",
        "v2_hybrid_rerank": "Keyword + embedding + Qwen3 reranker",
    }
    for key, item in versions.items():
        metric = item["metrics"]
        lines.append(
            f"| {key.split('_')[0].upper()} | {labels[key]} | {metric['hit_rate_at_1']:.1%} | "
            f"{metric['hit_rate_at_3']:.1%} | {metric['hit_rate_at_5']:.1%} | {metric['mrr_at_5']:.3f} | "
            f"{metric['abstention_accuracy']:.1%} | {metric['mean_latency_ms']} ms |"
        )
    lines += ["", "## Bad cases", ""]
    for key, item in versions.items():
        bad = []
        for row in item["rows"]:
            expected = set(row["pages"])
            retrieved = [hit["page_number"] for hit in row["hits"]]
            if row["answerable"] and not expected.intersection(retrieved):
                bad.append(f"- `{row['id']}` {row['question']} — expected {row['pages']}, retrieved {retrieved}")
        lines += [f"### {key}", "", *(bad or ["- No answerable Hit@5 failures."]), ""]
    lines += [
        "## Method",
        "",
        "- V0 ranks SQLite chunks with deterministic mixed Chinese/English keyword relevance.",
        "- V1 retrieves Qwen3 Embedding vectors from local Qdrant.",
        "- V2 merges both candidate sets, applies a Qwen3 0.6B listwise reranker with retrieval-score safeguards, then uses Qwen3 8B for evidence sufficiency.",
        "- A calibrated vector-similarity floor of 0.58 can override an overly conservative sufficiency rejection.",
        "- Page-level relevance labels were authored from the imported eight-page source PDF.",
        "- Latency is wall-clock time on the evaluation machine and should be compared directionally.",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--versions", nargs="+", default=["v0_keyword", "v1_embedding", "v2_hybrid_rerank"])
    parser.add_argument("--limit", type=int, default=0, help="Run only the first N questions for smoke tests")
    parser.add_argument("--force", action="store_true", help="Ignore cached rows for the selected versions")
    args = parser.parse_args()
    initialise()
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    if args.limit:
        questions = questions[: args.limit]
    chunks = load_chunks()
    if not chunks:
        raise SystemExit("No knowledge chunks found. Import the evaluation PDF first.")
    existing = json.loads(RESULTS_PATH.read_text(encoding="utf-8")) if RESULTS_PATH.exists() else {"versions": {}}
    versions: dict = existing.get("versions", {})
    searchers = {
        "v0_keyword": lambda q: keyword_search(q, chunks, 5),
        "v1_embedding": lambda q: vector_search(q, 5),
        "v2_hybrid_rerank": lambda q: hybrid_rerank(q, chunks, 5),
    }
    for version in args.versions:
        cached = {} if args.force else {row["id"]: row for row in versions.get(version, {}).get("rows", [])}
        rows = []
        for index, question in enumerate(questions, 1):
            if question["id"] in cached:
                rows.append(cached[question["id"]])
                continue
            started = time.perf_counter()
            result = {
                **question,
                "hits": serialise_hits(searchers[version](question["question"])),
                "latency_ms": round((time.perf_counter() - started) * 1000),
            }
            rows.append(result)
            versions[version] = {"rows": rows, "metrics": metrics(rows, version)}
            checkpoint = {
                "dataset_size": len(questions),
                "answerable": sum(item["answerable"] for item in questions),
                "unanswerable": sum(not item["answerable"] for item in questions),
                "versions": versions,
            }
            RESULTS_PATH.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[{version}] {index}/{len(questions)} {question['id']} {result['latency_ms']}ms", flush=True)
        versions[version] = {"rows": rows, "metrics": metrics(rows, version)}
    payload = {
        "dataset_size": len(questions),
        "answerable": sum(item["answerable"] for item in questions),
        "unanswerable": sum(not item["answerable"] for item in questions),
        "versions": versions,
    }
    RESULTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(payload)
    print(json.dumps({key: value["metrics"] for key, value in versions.items()}, indent=2))


if __name__ == "__main__":
    main()
