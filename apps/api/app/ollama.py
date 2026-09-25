import json
import re

import httpx

from .config import get_settings


class OllamaUnavailableError(RuntimeError):
    pass


def chat(system: str, prompt: str, *, json_output: bool = False, timeout: float = 120) -> str:
    settings = get_settings()
    payload = {
        "model": settings.ollama_model,
        "stream": False,
        "think": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "options": {"temperature": 0.1},
    }
    if json_output:
        payload["format"] = "json"
    try:
        response = httpx.post(f"{settings.ollama_base_url.rstrip('/')}/api/chat", json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, TypeError) as exc:
        raise OllamaUnavailableError(f"无法连接本地 Ollama 模型 {settings.ollama_model}") from exc


def classify_document(title: str, text: str, existing_categories: list[str]) -> tuple[str, str]:
    prompt = f"""文档标题：{title}
已有分类：{json.dumps(existing_categories, ensure_ascii=False)}
文档内容：
{text[:6000]}

请返回 JSON：
{{"category":"简短的中文分类名称","summary":"不超过80字的客观摘要"}}
优先复用合适的已有分类；没有合适分类时创建新分类。不要输出 JSON 之外的文字。"""
    raw = chat("你是个人知识库的文档整理助手。只依据给定文档分类和摘要。", prompt, json_output=True)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            raise OllamaUnavailableError("Qwen3 没有返回有效的分类结果")
        data = json.loads(match.group(0))
    category = str(data.get("category", "未分类")).strip()[:60] or "未分类"
    summary = str(data.get("summary", "")).strip()[:160] or text[:118].replace("\n", " ").strip()
    return category, summary


def answer_from_evidence(question: str, hits: list[dict]) -> str:
    evidence = "\n\n".join(f"[{index + 1}]《{hit['title']}》第{hit['page_number']}页\n{hit['text']}" for index, hit in enumerate(hits[:4]))
    prompt = f"""用户问题：{question}

知识库证据：
{evidence}

请直接回答问题。每个重要结论后标注对应来源编号，例如[1]。只能使用给定证据；证据无法支持的内容不要补充。"""
    return chat("你是严谨的个人知识库助手。回答必须可由引用证据验证。", prompt)


def rerank(question: str, candidates: list[dict], limit: int = 5) -> list[dict]:
    if not candidates:
        return []
    passages = "\n\n".join(f"ID={item['id']}\n{item['text'][:1200]}" for item in candidates[:20])
    prompt = f"""问题：{question}

候选片段：
{passages}

请判断每个片段是否直接有助于回答问题。返回 JSON：
{{"results":[{{"id":"片段ID","score":0到1之间的数字}}]}}
按相关性从高到低排列。不要输出其他文字。"""
    raw = chat("你是 RAG 二阶段重排器。优先选择直接回答问题、包含关键事实的证据。", prompt, json_output=True)
    data = json.loads(raw)
    scores = {str(item["id"]): max(0.0, min(1.0, float(item["score"]))) for item in data.get("results", [])}
    max_keyword = max((float(item.get("keyword_score", 0)) for item in candidates), default=0) or 1
    vector_values = [float(item.get("vector_score", 0)) for item in candidates]
    min_vector = min(vector_values, default=0)
    vector_range = (max(vector_values, default=0) - min_vector) or 1
    for item in candidates:
        keyword = float(item.get("keyword_score", 0)) / max_keyword
        vector = (float(item.get("vector_score", 0)) - min_vector) / vector_range
        retrieval = keyword * 0.6 + vector * 0.4
        item["score"] = retrieval * 0.65 + scores.get(item["id"], 0) * 0.35
    ranked = sorted(candidates, key=lambda item: item["score"], reverse=True)
    return ranked[:limit]
