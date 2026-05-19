# vector_store.py

import os
import chromadb
from openai import OpenAI
from config import (
    PROVIDER,
    OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL,
    OPENAI_API_KEY, OPENAI_EMBED_MODEL,
    TOP_K_CHUNKS,
)
from corpus import DOCUMENTS

# ---------------------------------------------------------------------------
# Provider setup — same pattern as before
# ---------------------------------------------------------------------------
if PROVIDER == "ollama":
    client      = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    EMBED_MODEL = OLLAMA_EMBED_MODEL
else:
    client      = OpenAI(api_key=OPENAI_API_KEY)
    EMBED_MODEL = OPENAI_EMBED_MODEL

CHUNK_SIZE     = 400
CHUNK_OVERLAP  = 80
CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION     = "rag_pipeline"


# ---------------------------------------------------------------------------
# Chunking — unchanged from Stage 2
# ---------------------------------------------------------------------------
def chunk_document(doc: dict) -> list[dict]:
    text   = doc["content"]
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

        start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks


# ---------------------------------------------------------------------------
# Embedding — unchanged from Stage 2
# ---------------------------------------------------------------------------
def embed_texts(texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


# ---------------------------------------------------------------------------
# ChromaDB vector store
# ---------------------------------------------------------------------------
# Key difference from Stage 2:
# ChromaDB persists to disk at CHROMA_DB_PATH. On first run it embeds
# everything and saves. On every subsequent run it loads from disk instantly
# — no embedding calls, no startup cost.

class VectorStore:
    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        self.collection    = self.chroma_client.get_or_create_collection(
            name=COLLECTION,
            # Tell ChromaDB we're supplying our own embeddings.
            # This keeps our provider abstraction intact — ChromaDB doesn't
            # call any embedding model itself.
            metadata={"hnsw:space": "cosine"},
        )

    def build(self, documents: list[dict]) -> None:
        """
        Embed and index all documents — but only if the collection is empty.
        This is the key production pattern: build once, reuse forever.
        """
        existing = self.collection.count()

        if existing > 0:
            print(f"Index already exists ({existing} chunks). Skipping build.")
            return

        print(f"Building index from {len(documents)} documents...")

        all_chunks = []
        for doc in documents:
            all_chunks.extend(chunk_document(doc))

        print(f"  {len(all_chunks)} chunks created")

        # Prepare parallel lists for ChromaDB
        ids        = []
        texts      = []
        embeddings = []
        metadatas  = []

        # Embed in one batch
        chunk_texts = [c["text"] for c in all_chunks]
        vectors     = embed_texts(chunk_texts)

        for i, (chunk, vector) in enumerate(zip(all_chunks, vectors)):
            ids.append(f"{chunk['doc_id']}_chunk_{chunk['chunk_index']}")
            texts.append(chunk["text"])
            embeddings.append(vector)
            metadatas.append({
                "doc_id":      chunk["doc_id"],
                "doc_title":   chunk["doc_title"],
                "chunk_index": chunk["chunk_index"],
            })

        # Upsert into ChromaDB
        # Upsert = insert if new, update if exists. Safe to call multiple times.
        self.collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        print(f"  Index built and persisted to {CHROMA_DB_PATH}")

    def retrieve(self, query: str, top_k: int = TOP_K_CHUNKS) -> list[dict]:
        """Embed the query and find the most similar chunks."""
        query_vector = embed_texts([query])[0]

        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        for text, metadata, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # ChromaDB returns cosine distance (0 = identical, 2 = opposite)
            # Convert to similarity score (1 = identical, -1 = opposite)
            score = 1 - distance

            chunks.append({
                "doc_id":    metadata["doc_id"],
                "doc_title": metadata["doc_title"],
                "text":      text,
                "score":     round(score, 3),
            })

        return chunks

    def list_documents(self) -> list[dict]:
        """
        Return one entry per unique source document.
        Used by the list_documents tool so the agent can explore the corpus.
        """
        results = self.collection.get(include=["metadatas"])

        seen  = {}
        for metadata in results["metadatas"]:
            doc_id = metadata["doc_id"]
            if doc_id not in seen:
                seen[doc_id] = metadata["doc_title"]

        return [{"id": k, "title": v} for k, v in sorted(seen.items())]

    def get_document(self, doc_id: str) -> dict | None:
        """
        Return all chunks for a specific document, reassembled into full text.
        Used by the get_document tool so the agent can read a full document.
        """
        results = self.collection.get(
            where={"doc_id": doc_id},
            include=["documents", "metadatas"],
        )

        if not results["ids"]:
            return None

        # Sort chunks by index and join
        chunks = sorted(
            zip(results["metadatas"], results["documents"]),
            key=lambda x: x[0]["chunk_index"],
        )

        full_text = "\n".join(text for _, text in chunks)
        title     = chunks[0][0]["doc_title"]

        return {"id": doc_id, "title": title, "content": full_text}


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_store = VectorStore()

def build_index() -> None:
    _store.build(DOCUMENTS)

def retrieve(query: str, top_k: int = TOP_K_CHUNKS) -> list[dict]:
    return _store.retrieve(query, top_k)

def list_documents() -> list[dict]:
    return _store.list_documents()

def get_document(doc_id: str) -> dict | None:
    return _store.get_document(doc_id)