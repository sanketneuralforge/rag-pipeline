# Research Assistant Agent

A production-grade RAG agent built end-to-end across 10 stages.
Each stage is a separate commit — read the history to watch the system evolve.

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

### What the ReAct loop looks like at runtime

```
============================================================
Question: What is the rollback procedure for a bad deployment?
============================================================

[Iteration 1]
  Tool call: retrieve_documents({'query': 'rollback procedure deployment'})
  Result preview: [1] Source: Production Deployment Runbook (relevance: 0.73)...

[Final Answer]
To rollback a deployment, run 'make rollback ENV=prod' from the repo root.
Page the on-call engineer if error rates don't stabilize within 10 minutes.
Source: Production Deployment Runbook
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
| 3 | ChromaDB + persistent index + 3 tools | 🔜 Next |
| 4 | Multi-agent orchestration | ⬜ Planned |
| 5 | Eval harness | ⬜ Planned |
| 6 | Guardrails + HITL | ⬜ Planned |
| 7 | Production redesign | ⬜ Planned |
| 8 | Observability + tracing | ⬜ Planned |
| 9 | Deployment | ⬜ Planned |
| 10 | Improvement loop | ⬜ Planned |