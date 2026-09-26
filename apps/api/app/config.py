from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_path: str = "recall.db"
    web_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:latest"
    reranker_model: str = "qwen3:0.6b"
    sufficiency_vector_floor: float = 0.58
    embedding_model: str = "qwen3-embedding:0.6b"
    qdrant_path: str = "qdrant_storage"
    qdrant_collection: str = "recall_chunks"
    uploads_path: str = "uploads"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
