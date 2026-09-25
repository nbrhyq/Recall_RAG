from app.ocr import _texts_from_result


class FakeResult:
    json = {"res": {"rec_texts": ["第一行", "RAG pipeline", ""]}}


def test_extracts_recognised_lines_from_paddle_result():
    assert _texts_from_result(FakeResult()) == ["第一行", "RAG pipeline"]
