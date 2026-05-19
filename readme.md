# Research Assistant Agent

A production-grade RAG agent built end-to-end across 10 stages.
Each stage is a separate commit — read the history to watch the system evolve.

---

## Stage 3 — Tools & Memory

### What this stage builds
Replaces the in-memory numpy vector store with ChromaDB for persistent storage.
Adds a real file loader replacing the inline corpus. Extends the agent from 1
tool to 3 tools, each with a distinct purpose.

### What changed from Stage 2

| | Stage 2 | Stage 3 |
|--|---------|---------|
| Vector store | numpy matrix in RAM | ChromaDB on disk |
| Index lifetime | Rebuilt every startup | Built once, reused forever |
| Corpus | Hardcoded inline strings | `.txt` files loaded from `docs/` |
| Tools | `retrieve_documents` only | + `list_documents` + `get_document` |

### Architecture

```
User question
     │
     ▼
┌─────────────────────────────────────────┐
│              ReAct Loop                 │
│         (max 3 iterations)              │
└─────────────────────────────────────────┘
     │
     ├──────────────────────────────────────┐
     ▼                                      ▼
retrieve_documents        list_documents / get_document
  (search by query)         (explore corpus by ID)
     │                                      │
     └──────────────┬───────────────────────┘
                    ▼
          ┌──────────────────┐
          │    ChromaDB      │
          │  (persisted to   │
          │   chroma_db/)    │
          └──────────────────┘
                    │
                    ▼
          Answer + source citations
```

### Files

| File | Purpose |
|------|---------|
| `config.py` | Provider config — unchanged from Stage 2 |
| `corpus.py` | File loader — reads `.txt` files from `docs/` |
| `docs/` | Document corpus — one `.txt` file per document |
| `vector_store.py` | ChromaDB index — build once, persist forever |
| `tools.py` | 3 tool schemas + executor |
| `agent.py` | ReAct loop — unchanged from Stage 2 |
| `main.py` | Entry point with 8 test questions |
| `chroma_db/` | Auto-generated — persisted vector index on disk |

### The 3 tools

**`retrieve_documents(query)`** — Semantic search. Embeds the query and returns
the top 3 most similar chunks from the corpus. First tool the agent calls for
any factual question.

**`list_documents()`** — Corpus explorer. Returns all document IDs and titles.
Agent calls this when the user asks what topics are covered, or when it needs
to find a document ID before calling `get_document`.

**`get_document(doc_id)`** — Full document reader. Returns the complete text of
a specific document reassembled from its chunks. Agent calls this when chunk
retrieval is insufficient and it needs to read the whole document.

### Key design decisions

**Build once, reuse forever** — `VectorStore.build()` checks if the collection
already has documents before embedding. On first run it embeds and persists.
Every subsequent run loads from disk instantly with zero API calls.

**Upsert not insert** — ChromaDB's `upsert()` is safe to call multiple times.
Insert would fail with duplicate ID errors if called twice. This matters in
production where you can't guarantee the index is empty.

**We supply our own embeddings** — ChromaDB is told `hnsw:space: cosine` but
we pass pre-computed vectors. This keeps provider abstraction intact — ChromaDB
never calls an embedding model itself.

**Cosine distance → similarity score** — ChromaDB returns distance (0 = identical).
We convert to similarity (1 = identical) with `score = 1 - distance` for
consistency with Stage 2 output.

### How to run

**Prerequisites**

- Python 3.12+
- Ollama running locally with `mistral` and `nomic-embed-text` pulled

```bash
ollama pull mistral
ollama pull nomic-embed-text
```

**Install dependencies**

```bash
pip install openai anthropic numpy chromadb python-dotenv
```

**Run**

```bash
python main.py
```

First run builds and persists the index. Every subsequent run skips the build:

```
Loaded 6 documents from .../docs
Index already exists (12 chunks). Skipping build.
```

**Switch providers**

Edit `config.py`:

```python
PROVIDER = "anthropic"  # or "openai" or "ollama"
```

**Reset the index**

Delete the `chroma_db/` folder and rerun. The index will rebuild from scratch:

```bash
rm -rf chroma_db/
python main.py
```

### Known limitations at this stage

- Tool selection is unreliable on smaller models (Mistral sometimes calls
  `retrieve_documents` when `get_document` is more appropriate)
- No query rewriting before first retrieval — vocabulary mismatch causes
  misses on the first attempt
- Single agent handles all reasoning — no specialization
- All three issues are addressed in Stage 4 with multi-agent orchestration

### Concepts this stage teaches

- Why in-memory vector stores break in production (cost, latency, scale)
- ChromaDB persistent collections — build once, query forever
- Upsert vs insert for idempotent index builds
- Tool description quality directly affects which tool the agent calls
- The difference between search (retrieve_documents) and read (get_document)

---

## Stage 2 — Minimal Working Agent (MVP)

### What this stage builds
A fully working RAG agent from scratch using raw API calls and no frameworks.
The core ReAct loop is implemented by hand so every abstraction is visible.

### Architecture

```
User question
     │
     ▼
┌─────────────────────────────────┐
│           ReAct Loop            │
│                                 │
│  Think → Act → Observe → Think  │
│       (max 3 iterations)        │
└─────────────────────────────────┘
          │              │
          ▼              ▼
  ┌──────────────┐  ┌─────────────────────┐
  │  LLM (chat)  │  │    Vector Store     │
  │    Mistral   │  │  numpy + cosine sim │
  │   /Claude    │  └─────────────────────┘
  └──────────────┘
          │
          ▼
  Answer + source citations
```

### Files

| File | Purpose |
|------|---------|
| `config.py` | Single-file provider config — swap Ollama / Anthropic / OpenAI here |
| `corpus.py` | Inline document corpus (6 company documents) |
| `vector_store.py` | Chunking, embedding, cosine similarity retrieval |
| `tools.py` | Tool schema (JSON) + tool executor |
| `agent.py` | ReAct loop + provider-abstracted LLM calls |
| `main.py` | Entry point with 6 test questions |

### Key design decisions

**Provider abstraction** — One config value (`PROVIDER`) switches between
Ollama (local), Anthropic, and OpenAI. Zero changes to agent logic required.

**Manual ReAct loop** — No LangGraph or LlamaIndex. The loop is a plain
while loop that appends to a messages list. This is exactly what every
framework abstracts.

**In-memory vector store** — Chunks are embedded at startup and stored as
a numpy matrix. Cosine similarity is computed via normalised dot product.
Replaced by ChromaDB in Stage 3.

**Chunking with overlap** — Documents are split into 400-character chunks
with 80-character overlap. Overlap prevents key facts from being cut at
chunk boundaries.

### How to run

**Prerequisites**

- Python 3.12+
- Ollama running locally with `mistral` and `nomic-embed-text` pulled

```bash
ollama pull mistral
ollama pull nomic-embed-text
```

**Install dependencies**

```bash
pip install openai anthropic numpy python-dotenv
```

**Run**

```bash
python main.py
```

**Switch providers**

Edit `config.py`:

```python
PROVIDER = "anthropic"  # or "openai" or "ollama"
```

### Known limitations at this stage

- Index is rebuilt from scratch on every run (fixed in Stage 3 with ChromaDB)
- Corpus is hardcoded inline (fixed in Stage 3 with a file loader)
- Single retrieval tool only (fixed in Stage 3 with `list_documents` + `get_document` tools)
- Mistral sometimes skips tool calls on ambiguous questions (mitigated with explicit system prompt rules)

### Concepts this stage teaches

- ReAct loop mechanics (Reason + Act)
- Tool calling at the API level — how the LLM requests a tool vs how your code executes it
- Chunking and why document size matters for retrieval precision
- Cosine similarity vs euclidean distance for text search
- Provider abstraction pattern

---

## Stages

| Stage | What it builds | Status |
|-------|----------------|--------|
| 1 | Problem framing + system design doc | ✅ Done |
| 2 | MVP ReAct agent + in-memory RAG | ✅ Done |
| 3 | ChromaDB + persistent index + 3 tools | ✅ Done |
| 4 | Multi-agent orchestration | 🔜 Next |
| 5 | Eval harness | ⬜ Planned |
| 6 | Guardrails + HITL | ⬜ Planned |
| 7 | Production redesign | ⬜ Planned |
| 8 | Observability + tracing | ⬜ Planned |
| 9 | Deployment | ⬜ Planned |
| 10 | Improvement loop | ⬜ Planned |