from datetime import datetime

from pydantic import BaseModel, Field


class TextCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    content: str = Field(min_length=10, max_length=100_000)


class Document(BaseModel):
    id: str
    url: str
    title: str
    author: str
    collection: str
    summary: str
    transcript: str
    duration: float
    status: str
    created_at: datetime
    source_type: str = "pdf"
    file_name: str | None = None
    page_count: int = 0


class Citation(BaseModel):
    document_id: str
    title: str
    author: str
    url: str
    start: float
    end: float
    quote: str
    score: float
    source_type: str = "pdf"
    file_name: str | None = None
    page_number: int | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    collection: str | None = None


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    grounded: bool
    confidence: float
