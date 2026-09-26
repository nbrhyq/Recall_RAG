import json
import re

import httpx

from .config import get_settings


class OllamaUnavailableError(RuntimeError):
    pass


def chat(system: str, prompt: str, *, json_output: bool = False, timeout: float = 120, model: str | None = None) -> str:
    settings = get_settings()
    selected_model = model or settings.ollama_model
    payload = {
        "model": selected_model,
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
        raise OllamaUnavailableError(f"无法连接本地 Ollama 模型 {selected_model}") from exc


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
    max_keyword = max((float(item.get("keyword_score", 0)) for item in candidates), default=0) or 1
    vector_values = [float(item.get("vector_score", 0)) for item in candidates]
    min_vector = min(vector_values, default=0)
    vector_range = (max(vector_values, default=0) - min_vector) or 1
    for item in candidates:
        keyword = float(item.get("keyword_score", 0)) / max_keyword
        vector = (float(item.get("vector_score", 0)) - min_vector) / vector_range
        item["retrieval_score"] = keyword * 0.6 + vector * 0.4
    candidates = sorted(candidates, key=lambda item: item["retrieval_score"], reverse=True)[:10]
    passages = "\n\n".join(f"ID={item['id']}\n{item['text'][:600]}" for item in candidates)
    prompt = f"""问题：{question}

候选片段：
{passages}

请先判断候选证据是否足以回答问题，再按“能否直接回答问题”从高到低排列片段。只返回 JSON：
{{"answerable":true或false,"ranking":["最相关片段ID","第二相关片段ID"]}}
必须使用原始 ID，不要打分，不要输出其他文字。"""
    raw = chat(
        "你是 RAG 二阶段重排器。优先选择直接回答问题、包含关键事实的证据。",
        prompt,
        json_output=True,
        model=get_settings().reranker_model,
    )
    data = json.loads(raw)
    ranking = [str(item) for item in data.get("ranking", [])]
    if not ranking and data.get("results"):
        ranking = [str(item["id"]) for item in sorted(data["results"], key=lambda item: float(item.get("score", 0)), reverse=True)]
    positions = {item_id: index for index, item_id in enumerate(ranking)}
    evidence = "\n\n".join(item["text"][:350] for item in candidates[:3])
    sufficiency_raw = chat(
        "你是严格的知识库证据充分性分类器。",
        f"""问题：{question}

候选证据：
{evidence}

只有证据明确包含问题所需的具体事实时才返回 true。主题相似但缺少答案必须返回 false。
只返回 JSON：{{"answerable":true或false}}""",
        json_output=True,
        model=get_settings().ollama_model,
    )
    answerable_value = json.loads(sufficiency_raw).get("answerable", True)
    if isinstance(answerable_value, str):
        answerable = answerable_value.strip().lower() not in {"false", "no", "0", "否", "不可回答"}
    else:
        answerable = bool(answerable_value)
    answerable = answerable or max(vector_values, default=0) >= get_settings().sufficiency_vector_floor
    answerable_factor = 1.0 if answerable else 0.2
    for item in candidates:
        reranker_score = 1 - positions.get(item["id"], len(candidates)) / max(1, len(candidates))
        item["score"] = (item["retrieval_score"] * 0.8 + reranker_score * 0.2) * answerable_factor
    ranked = sorted(candidates, key=lambda item: item["score"], reverse=True)
    return ranked[:limit]
