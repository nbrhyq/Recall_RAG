from app.rag import chunk_segments, make_segments, relevance, tokenise


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

