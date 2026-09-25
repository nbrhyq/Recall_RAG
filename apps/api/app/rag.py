import math
import re
from collections import Counter


STOPWORDS = {"的", "了", "是", "在", "和", "与", "为什么", "什么", "怎么", "如何", "一个", "这个", "可以", "主要"}


def tokenise(text: str) -> list[str]:
    latin = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]+", text.lower())
    chinese = re.findall(r"[\u4e00-\u9fff]", text)
    bigrams = ["".join(chinese[i : i + 2]) for i in range(len(chinese) - 1)]
    return [t for t in latin + bigrams if t not in STOPWORDS]


def make_segments(transcript: str, supplied: list[dict] | None = None) -> list[dict]:
    if supplied:
        return supplied
    sentences = [part.strip() for part in re.split(r"(?<=[。！？!?])", transcript) if part.strip()]
    if not sentences:
        sentences = [transcript]
    result, cursor = [], 0.0
    for sentence in sentences:
        duration = max(4.0, len(sentence) / 4.2)
        result.append({"start": cursor, "end": cursor + duration, "text": sentence})
        cursor += duration
    return result


def chunk_segments(segments: list[dict], target_chars: int = 240) -> list[dict]:
    chunks, current = [], []
    size = 0
    for segment in segments:
        current.append(segment)
        size += len(segment["text"])
        if size >= target_chars:
            chunks.append(_merge(current))
            current, size = [], 0
    if current:
        chunks.append(_merge(current))
    return chunks


def _merge(items: list[dict]) -> dict:
    return {"start": items[0]["start"], "end": items[-1]["end"], "text": "".join(i["text"] for i in items)}


def relevance(question: str, text: str) -> float:
    q, d = Counter(tokenise(question)), Counter(tokenise(text))
    if not q or not d:
        return 0.0
    overlap = sum(min(q[t], d[t]) for t in q)
    cosine = overlap / math.sqrt(sum(q.values()) * sum(d.values()))
    exact_bonus = 0.25 if any(token in text.lower() for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]+", question.lower())) else 0
    return min(1.0, cosine * 1.5 + exact_bonus)


def grounded_answer(question: str, hits: list[dict]) -> str:
    if not hits or hits[0]["score"] < 0.12:
        return "当前文档内容不足以可靠回答这个问题。你可以添加相关 PDF 后再试，我不会用知识库之外的信息补全答案。"
    evidence = [hit["text"].strip() for hit in hits[:3]]
    joined = "\n\n".join(f"{index + 1}. {text}" for index, text in enumerate(evidence))
    return f"根据你的文档，和“{question}”最相关的信息是：\n\n{joined}\n\n以上结论仅基于下方引用的 PDF 片段。"
