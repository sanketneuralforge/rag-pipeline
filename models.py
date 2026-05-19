from pydantic import BaseModel
from typing import Optional


class Document(BaseModel):
    id: str
    content: str
    source: str
    metadata: dict = {}


class Chunk(BaseModel):
    id: str
    doc_id: str
    content: str
    source: str
    chunk_index: int
    metadata: dict = {}


class RetrievedChunk(BaseModel):
    chunk: Chunk
    score: float


class RAGResponse(BaseModel):
    question: str
    answer: str
    sources: list[RetrievedChunk]
    model: str
