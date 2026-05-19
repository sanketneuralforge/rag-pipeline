# vector_store.py

import numpy as np
from openai import OpenAI
from config import (
    PROVIDER,
    OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL,
    OPENAI_API_KEY, OPENAI_EMBED_MODEL,
    TOP_K_CHUNKS,
)
from corpus import DOCUMENTS

# ---------------------------------------------------------------------------
# Provider setup
# Ollama exposes an OpenAI-compatible API, so we use the same OpenAI client
# for both — just swap the base_url and model name.
# ---------------------------------------------------------------------------
if PROVIDER == "ollama":
    client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    EMBED_MODEL = OLLAMA_EMBED_MODEL
elif PROVIDER == "openai":
    client = OpenAI(api_key=OPENAI_API_KEY)
    EMBED_MODEL = OPENAI_EMBED_MODEL
else:
    # Anthropic doesn't have an embedding model, so we fall back to OpenAI
    # for embeddings even when using Claude for chat. This is a real pattern
    # used in production.
    client = OpenAI(api_key=OPENAI_API_KEY)
    EMBED_MODEL = OPENAI_EMBED_MODEL

CHUNK_SIZE    = 400   # characters per chunk
CHUNK_OVERLAP = 80    # overlap between adjacent chunks


# ---------------------------------------------------------------------------
# Step 1: Chunking
# ---------------------------------------------------------------------------
def chunk_document(doc: dict) -> list[dict]:
    text  = doc["content"]
    chunks = []
    start  = 0

    while start < len(text):
        end        = min(start + CHUNK_SIZE, len(text))
        chunk_text = text[start:end].strip()

        if chunk_text:
            chunks.append({
                "doc_id":      doc["id"],
                "doc_title":   doc["title"],
                "chunk_index": len(chunks),
                "text":        chunk_text,
            })

        if end == len(text):
            break

        start += CHUNK_SIZE - CHUNK_OVERLAP   # slide forward with overlap

    return chunks


# ---------------------------------------------------------------------------
# Step 2: Embedding
# ---------------------------------------------------------------------------
def embed_texts(texts: list[str]) -> np.ndarray:
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=texts,
    )
    vectors = [item.embedding for item in response.data]
    return np.array(vectors, dtype=np.float32)


# ---------------------------------------------------------------------------
# Step 3: Index + Retrieval
# ---------------------------------------------------------------------------
class VectorStore:
    def __init__(self):
        self.chunks: list[dict]       = []
        self.matrix: np.ndarray | None = None

    def build(self, documents: list[dict]) -> None:
        print(f"Building index from {len(documents)} documents...")

        all_chunks = []
        for doc in documents:
            all_chunks.extend(chunk_document(doc))

        print(f"  {len(all_chunks)} chunks created")

        texts        = [c["text"] for c in all_chunks]
        vectors      = embed_texts(texts)

        self.chunks  = all_chunks
        self.matrix  = vectors

        print(f"  Index built — matrix shape: {self.matrix.shape}")

    def retrieve(self, query: str, top_k: int = TOP_K_CHUNKS) -> list[dict]:
        if self.matrix is None:
            raise RuntimeError("Call build() before retrieve()")

        query_vec = embed_texts([query])[0]

        # Cosine similarity via normalised dot product
        doc_norms   = np.linalg.norm(self.matrix, axis=1, keepdims=True)
        query_norm  = np.linalg.norm(query_vec)
        norm_matrix = self.matrix / (doc_norms + 1e-10)
        norm_query  = query_vec   / (query_norm + 1e-10)
        scores      = norm_matrix @ norm_query          # shape (N,)

        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            chunk          = dict(self.chunks[idx])
            chunk["score"] = float(scores[idx])
            results.append(chunk)

        return results


# ---------------------------------------------------------------------------
# Module-level singleton — build once at startup, reuse everywhere
# ---------------------------------------------------------------------------
_store = VectorStore()

def build_index() -> None:
    _store.build(DOCUMENTS)

def retrieve(query: str, top_k: int = TOP_K_CHUNKS) -> list[dict]:
    return _store.retrieve(query, top_k)