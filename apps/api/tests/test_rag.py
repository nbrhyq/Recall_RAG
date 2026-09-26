from app.rag import chunk_segments, make_segments, relevance, tokenise
from app import ollama


def test_mixed_language_tokenisation():
    tokens = tokenise("RAG 中 reranker 的作用是什么？")
    assert "rag" in tokens
    assert "reranker" in tokens


def test_relevant_text_scores_higher():
    question = "reranker 有什么作用"
    relevant = relevance(question, "reranker 会对候选文档重新排序")
    irrelevant = relevance(question, "英伟达公布了季度财报")
    assert relevant > irrelevant


def test_segments_preserve_timestamps():
    chunks = chunk_segments(make_segments("第一句话。第二句话。"), target_chars=4)
    assert chunks[0]["start"] == 0
    assert chunks[-1]["end"] > chunks[0]["start"]


def test_reranker_keeps_strong_retrieval_evidence(monkeypatch):
    monkeypatch.setattr(
        ollama,
        "chat",
        lambda *args, **kwargs: '{"answerable":true,"ranking":["weak","exact"]}',
    )
    candidates = [
        {"id": "exact", "text": "RAG 是外置知识库", "keyword_score": 0.5, "vector_score": 0.9},
        {"id": "weak", "text": "不相关内容", "keyword_score": 0.0, "vector_score": 0.1},
    ]
    assert ollama.rerank("什么是 RAG", candidates, limit=1)[0]["id"] == "exact"


def test_reranker_parses_string_false_as_insufficient(monkeypatch):
    monkeypatch.setattr(
        ollama,
        "chat",
        lambda *args, **kwargs: '{"answerable":"false","ranking":["weak"]}',
    )
    hits = ollama.rerank(
        "资料没有的问题",
        [{"id": "weak", "text": "相似但不支持", "keyword_score": 0.2, "vector_score": 0.5}],
        limit=1,
    )
    assert hits[0]["score"] < 0.25
