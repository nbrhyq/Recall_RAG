from functools import lru_cache

import httpx
from qdrant_client import QdrantClient, models

from .config import get_settings
from .ollama import OllamaUnavailableError


@lru_cache(maxsize=1)
def client() -> QdrantClient:
    return QdrantClient(path=get_settings().qdrant_path)


def embed(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    try:
        response = httpx.post(
            f"{settings.ollama_base_url.rstrip('/')}/api/embed",
            json={"model": settings.embedding_model, "input": texts},
            timeout=180,
        )
        response.raise_for_status()
        return response.json()["embeddings"]
    except (httpx.HTTPError, KeyError, TypeError) as exc:
        raise OllamaUnavailableError(f"无法调用 Embedding 模型 {settings.embedding_model}") from exc


def index_chunks(chunks: list[dict]) -> None:
    if not chunks:
        return
    vectors = embed([chunk["text"] for chunk in chunks])
    settings = get_settings()
    db = client()
    if not db.collection_exists(settings.qdrant_collection):
        db.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=models.VectorParams(size=len(vectors[0]), distance=models.Distance.COSINE),
        )
    db.upsert(
        collection_name=settings.qdrant_collection,
        wait=True,
        points=[models.PointStruct(id=chunk["id"], vector=vector, payload=chunk) for chunk, vector in zip(chunks, vectors)],
    )


def semantic_search(question: str, limit: int = 20) -> list[dict]:
    settings = get_settings()
    db = client()
    if not db.collection_exists(settings.qdrant_collection):
        return []
    vector = embed([question])[0]
    results = db.query_points(collection_name=settings.qdrant_collection, query=vector, limit=limit, with_payload=True).points
    return [{**(point.payload or {}), "vector_score": float(point.score)} for point in results]


def delete_document(document_id: str) -> None:
    settings = get_settings()
    db = client()
    if not db.collection_exists(settings.qdrant_collection):
        return
    db.delete(
        collection_name=settings.qdrant_collection,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
            )
        ),
        wait=True,
    )
