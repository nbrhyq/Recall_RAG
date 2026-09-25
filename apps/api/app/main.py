import json
import re
import unicodedata
import uuid
from io import BytesIO
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pypdf import PdfReader

from .config import get_settings
from .database import connection, initialise, row_dict
from .models import AskRequest, AskResponse, Citation, Document, TextCreate
from .ocr import OCRUnavailableError, extract_image, extract_scanned_pages
from .ollama import OllamaUnavailableError, answer_from_evidence, classify_document, rerank
from .rag import grounded_answer, relevance, tokenise
from .vector_store import delete_document as delete_vectors, index_chunks, semantic_search


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialise()
    yield


app = FastAPI(title="Recall API", version="0.1.0", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.web_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _clean_extracted_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", text).strip()


@app.get("/health")
def health():
    return {"status": "ok", "mode": "local", "llm": settings.ollama_model, "embedding": settings.embedding_model, "vector_store": "qdrant-local", "reranker": settings.ollama_model, "ollama_url": settings.ollama_base_url}


@app.get("/api/documents", response_model=list[Document])
def list_documents():
    with connection() as conn:
        rows = conn.execute("SELECT id, url, title, author, collection_name AS collection, summary, transcript, duration, status, created_at, source_type, file_name, page_count FROM videos WHERE source_type != 'video' ORDER BY created_at DESC").fetchall()
    return [Document(**row_dict(row)) for row in rows]


def _stored_file(document_id: str, source_type: str, file_name: str | None) -> Path:
    suffix = Path(file_name or "").suffix.lower()
    if not suffix:
        suffix = ".pdf" if source_type == "pdf" else ".bin"
    return Path(settings.uploads_path) / f"{document_id}{suffix}"


@app.get("/api/documents/{document_id}/file")
def get_document_file(document_id: str):
    with connection() as conn:
        row = conn.execute(
            "SELECT source_type, file_name FROM videos WHERE id = ? AND source_type IN ('pdf', 'image')",
            (document_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "文件不存在")
    path = _stored_file(document_id, row["source_type"], row["file_name"])
    if not path.exists():
        raise HTTPException(404, "原文件未保存；请重新导入该内容")
    media_type = "application/pdf" if row["source_type"] == "pdf" else None
    return FileResponse(path, filename=row["file_name"], media_type=media_type)


@app.delete("/api/documents/{document_id}", status_code=204)
def delete_document(document_id: str):
    with connection() as conn:
        row = conn.execute(
            "SELECT source_type, file_name FROM videos WHERE id = ? AND source_type != 'video'", (document_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "知识条目不存在")
        conn.execute("DELETE FROM videos WHERE id = ?", (document_id,))
    delete_vectors(document_id)
    path = _stored_file(document_id, row["source_type"], row["file_name"])
    path.unlink(missing_ok=True)
    return Response(status_code=204)


@app.post("/api/pdfs", response_model=Document, status_code=201)
async def add_pdf(
    file: UploadFile = File(...),
    title: str = Form(""),
):
    filename = file.filename or "document.pdf"
    if file.content_type != "application/pdf" and not filename.lower().endswith(".pdf"):
        raise HTTPException(415, "只支持 PDF 文件")
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(413, "PDF 不能超过 20MB")
    try:
        reader = PdfReader(BytesIO(content))
        if len(reader.pages) > 100:
            raise HTTPException(413, "PDF 不能超过 100 页")
        all_pages = [(index + 1, _clean_extracted_text(page.extract_text() or "")) for index, page in enumerate(reader.pages)]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, "无法读取这个 PDF，请确认文件没有损坏或加密") from exc
    scanned_pages = {number for number, text in all_pages if len(text) < 8}
    if scanned_pages:
        try:
            ocr_pages = extract_scanned_pages(content, scanned_pages)
        except OCRUnavailableError as exc:
            raise HTTPException(503, str(exc)) from exc
        all_pages = [(number, _clean_extracted_text(ocr_pages.get(number, text))) for number, text in all_pages]
    pages = [(number, text) for number, text in all_pages if text]
    if not pages:
        raise HTTPException(422, "没有从这个 PDF 识别到文字，请检查扫描清晰度")

    document_id = str(uuid.uuid4())
    created = datetime.now(timezone.utc)
    document_title = title.strip() or filename.rsplit(".", 1)[0]
    transcript = "\n\n".join(text for _, text in pages)
    with connection() as conn:
        existing_categories = [row[0] for row in conn.execute("SELECT DISTINCT collection_name FROM videos WHERE source_type != 'video' AND collection_name != '未分类'").fetchall()]
    try:
        collection, summary = classify_document(document_title, transcript, existing_categories)
    except OllamaUnavailableError as exc:
        raise HTTPException(503, f"PDF 已成功解析，但{exc}。请先运行 ollama serve") from exc
    vector_chunks: list[dict] = []
    stored_path = _stored_file(document_id, "pdf", filename)
    stored_path.parent.mkdir(parents=True, exist_ok=True)
    stored_path.write_bytes(content)
    try:
        with connection() as conn:
            conn.execute(
                "INSERT INTO videos (id, url, title, author, collection_name, summary, transcript, duration, status, created_at, source_type, file_name, page_count) VALUES (?, ?, ?, 'PDF 文档', ?, ?, ?, 0, 'ready', ?, 'pdf', ?, ?)",
                (document_id, f"pdf://{document_id}", document_title, collection, summary, transcript, created.isoformat(), filename, len(reader.pages)),
            )
            for page_number, page_text in pages:
                paragraphs = [part.strip() for part in page_text.splitlines() if part.strip()]
                buffer = ""
                page_chunks: list[str] = []
                for paragraph in paragraphs:
                    if buffer and len(buffer) + len(paragraph) > 420:
                        page_chunks.append(buffer)
                        buffer = paragraph
                    else:
                        buffer = f"{buffer}\n{paragraph}".strip()
                if buffer:
                    page_chunks.append(buffer)
                for text in page_chunks:
                    chunk_id = str(uuid.uuid4())
                    conn.execute(
                        "INSERT INTO chunks (id, video_id, start_time, end_time, text, tokens, page_number) VALUES (?, ?, 0, 0, ?, ?, ?)",
                        (chunk_id, document_id, text, json.dumps(tokenise(text), ensure_ascii=False), page_number),
                    )
                    vector_chunks.append({"id": chunk_id, "document_id": document_id, "title": document_title, "author": "PDF 文档", "url": f"pdf://{document_id}", "source_type": "pdf", "file_name": filename, "page_number": page_number, "start_time": 0, "end_time": 0, "text": text})
            index_chunks(vector_chunks)
    except OllamaUnavailableError as exc:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(503, f"文档未保存：{exc}。请确认已安装 Embedding 模型") from exc
    return Document(id=document_id, url=f"pdf://{document_id}", title=document_title, author="PDF 文档", collection=collection, summary=summary, transcript=transcript, duration=0, status="ready", created_at=created, source_type="pdf", file_name=filename, page_count=len(reader.pages))


def _existing_categories() -> list[str]:
    with connection() as conn:
        return [row[0] for row in conn.execute("SELECT DISTINCT collection_name FROM videos WHERE source_type != 'video' AND collection_name != '未分类'").fetchall()]


def _plain_chunks(text: str, size: int = 420) -> list[str]:
    paragraphs = [part.strip() for part in text.splitlines() if part.strip()]
    chunks: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        if buffer and len(buffer) + len(paragraph) > size:
            chunks.append(buffer)
            buffer = paragraph
        else:
            buffer = f"{buffer}\n{paragraph}".strip()
    if buffer:
        chunks.append(buffer)
    return chunks or [text]


def _save_non_pdf(title: str, text: str, source_type: str, file_name: str | None = None, content: bytes | None = None) -> Document:
    try:
        collection, summary = classify_document(title, text, _existing_categories())
    except OllamaUnavailableError as exc:
        raise HTTPException(503, f"内容已成功读取，但{exc}。请先运行 ollama serve") from exc
    document_id = str(uuid.uuid4())
    created = datetime.now(timezone.utc)
    page_count = 1 if source_type == "image" else 0
    vector_chunks: list[dict] = []
    with connection() as conn:
        conn.execute(
            "INSERT INTO videos (id, url, title, author, collection_name, summary, transcript, duration, status, created_at, source_type, file_name, page_count) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 'ready', ?, ?, ?, ?)",
            (document_id, f"{source_type}://{document_id}", title, "图片 OCR" if source_type == "image" else "手动文本", collection, summary, text, created.isoformat(), source_type, file_name, page_count),
        )
        for chunk in _plain_chunks(text):
            chunk_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO chunks (id, video_id, start_time, end_time, text, tokens, page_number) VALUES (?, ?, 0, 0, ?, ?, ?)",
                (chunk_id, document_id, chunk, json.dumps(tokenise(chunk), ensure_ascii=False), 1 if source_type == "image" else None),
            )
            vector_chunks.append({"id": chunk_id, "document_id": document_id, "title": title, "author": "图片 OCR" if source_type == "image" else "手动文本", "url": f"{source_type}://{document_id}", "source_type": source_type, "file_name": file_name, "page_number": 1 if source_type == "image" else None, "start_time": 0, "end_time": 0, "text": chunk})
        try:
            index_chunks(vector_chunks)
        except OllamaUnavailableError as exc:
            raise HTTPException(503, f"内容未保存：{exc}。请确认已安装 Embedding 模型") from exc
    if content is not None:
        stored_path = _stored_file(document_id, source_type, file_name)
        stored_path.parent.mkdir(parents=True, exist_ok=True)
        stored_path.write_bytes(content)
    return Document(id=document_id, url=f"{source_type}://{document_id}", title=title, author="图片 OCR" if source_type == "image" else "手动文本", collection=collection, summary=summary, transcript=text, duration=0, status="ready", created_at=created, source_type=source_type, file_name=file_name, page_count=page_count)


@app.post("/api/texts", response_model=Document, status_code=201)
def add_text(payload: TextCreate):
    return _save_non_pdf(payload.title, payload.content, "text")


@app.post("/api/images", response_model=Document, status_code=201)
async def add_image(file: UploadFile = File(...), title: str = Form("")):
    filename = file.filename or "image.png"
    allowed = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
    suffix = allowed.get(file.content_type or "")
    if not suffix:
        raise HTTPException(415, "只支持 PNG、JPG 和 WebP 图片")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "图片不能超过 10MB")
    try:
        text = extract_image(content, suffix)
    except OCRUnavailableError as exc:
        raise HTTPException(503, str(exc)) from exc
    if len(text.strip()) < 4:
        raise HTTPException(422, "没有从图片中识别到足够文字")
    return _save_non_pdf(title.strip() or filename.rsplit(".", 1)[0], text, "image", filename, content)


@app.post("/api/ask", response_model=AskResponse)
def ask(payload: AskRequest):
    query = """
      SELECT c.id, c.video_id AS document_id, c.start_time, c.end_time, c.text, c.page_number, v.title, v.author, v.url, v.source_type, v.file_name
      FROM chunks c JOIN videos v ON v.id = c.video_id
      WHERE v.source_type != 'video'
    """
    params: tuple = ()
    if payload.collection:
        query += " AND v.collection_name = ?"
        params = (payload.collection,)
    with connection() as conn:
        rows = [row_dict(row) for row in conn.execute(query, params).fetchall()]
    keyword_hits = sorted(({**row, "keyword_score": relevance(payload.question, row["text"])} for row in rows), key=lambda item: item["keyword_score"], reverse=True)[:20]
    try:
        vector_hits = semantic_search(payload.question, limit=20)
        merged = {item["id"]: item for item in vector_hits}
        for item in keyword_hits:
            merged[item["id"]] = {**merged.get(item["id"], {}), **item}
        hits = rerank(payload.question, list(merged.values()), limit=4)
    except OllamaUnavailableError as exc:
        raise HTTPException(503, f"{exc}。请确认 Ollama 和检索模型正在运行") from exc
    grounded = bool(hits and hits[0]["score"] >= 0.25)
    citations = [Citation(document_id=h["document_id"], title=h["title"], author=h["author"], url=h["url"], start=h["start_time"], end=h["end_time"], quote=h["text"], score=round(h["score"], 3), source_type=h["source_type"], file_name=h["file_name"], page_number=h["page_number"]) for h in hits if h["score"] >= 0.08]
    confidence = round(sum(c.score for c in citations[:3]) / max(1, min(3, len(citations))), 2) if grounded else 0
    if grounded:
        try:
            answer = answer_from_evidence(payload.question, hits)
        except OllamaUnavailableError as exc:
            raise HTTPException(503, f"{exc}。请先运行 ollama serve") from exc
    else:
        answer = grounded_answer(payload.question, hits)
    return AskResponse(answer=answer, citations=citations, grounded=grounded, confidence=confidence)
