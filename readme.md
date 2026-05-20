# Research Assistant Agent

A production-grade RAG agent built end-to-end across 10 stages.
Each stage is a separate commit — read the history to watch the system evolve.

---

## Stage 4 — Multi-Agent Orchestration

### What this stage builds
Breaks the single ReAct agent into three specialized sub-agents coordinated
by an orchestrator. Each agent has exactly one job. The orchestrator manages
shared state and sequential handoff between agents.

### What changed from Stage 3

| | Stage 3 | Stage 4 |
|--|---------|---------|
| Architecture | Single ReAct agent | Orchestrator + 3 sub-agents |
| Query strategy | One query per question | 2-3 rewritten queries per question |
| Tool selection | Agent decides everything | Retriever agent decides retrieval only |
| Answer writing | Same agent that retrieves | Dedicated Synthesizer agent |
| Failure mode | One agent drops responsibilities | Each agent fails independently |

### Architecture

```
User question
     │
     ▼
┌─────────────────────────────────────────────┐
│                 Orchestrator                │
│   manages shared state, sequential handoff  │
└─────────────────────────────────────────────┘
     │
     ▼ step 1
┌─────────────────────┐
│    Query Rewriter   │  rewrites question into 2-3 optimized search queries
└─────────────────────┘
     │ rewritten queries
     ▼ step 2
┌─────────────────────┐
│      Retriever      │  executes tool calls, decides retrieve vs get_document
└─────────────────────┘
     │         │
     ▼         ▼
 retrieve   get_document
 _documents  (ChromaDB)
     │         │
     └────┬────┘
          │ retrieved chunks
          ▼ step 3
┌─────────────────────┐
│     Synthesizer     │  writes grounded answer with citations
└─────────────────────┘
     │
     ▼
Answer + source citations
```

### Files

| File | Purpose |
|------|---------|
| `config.py` | Provider config — unchanged |
| `corpus.py` | File loader — unchanged |
| `docs/` | Document corpus — unchanged |
| `vector_store.py` | ChromaDB index — unchanged |
| `tools.py` | 3 tools + execute_tool with list/string query guard |
| `agents/__init__.py` | Package marker |
| `agents/query_rewriter.py` | Rewrites question into optimized search queries |
| `agents/retriever.py` | Executes tool calls, returns retrieved chunks |
| `agents/synthesizer.py` | Writes grounded answer with citations |
| `agents/orchestrator.py` | Coordinates sub-agents, manages shared state |
| `agent.py` | Stage 2/3 single agent — kept for comparison |
| `main.py` | Entry point — now calls orchestrator |

### The 3 sub-agents

**Query Rewriter** — Takes the user's raw question and returns 2-3 short,
focused search queries using different vocabulary. Fixes vocabulary mismatch
between what users say and what documents contain. Returns JSON array of
query strings.

**Retriever** — Takes the rewritten queries and executes tool calls against
ChromaDB. Decides whether to use `retrieve_documents` (semantic search) or
`get_document` (full document read). Returns all retrieved chunks as a single
formatted string.

**Synthesizer** — Takes the original question and all retrieved chunks. Writes
a concise, grounded answer with source citations. Returns "I could not find an
answer in the available documents." when context is insufficient.

### Shared state

The orchestrator passes a state dict forward through each step:

```python
state = {
    "question":          "How many PTO days do employees get?",
    "rewritten_queries": ["PTO accrual days", "paid leave entitlement", ...],
    "retrieved_chunks":  "[1] Source: PTO & Leave Policy ...",
    "final_answer":      "Full-time employees accrue 15 days...",
}
```

No message queues. No async. Plain sequential handoff — the simplest pattern
that solves the problem.

### Key design decisions

**Specialization over generalization** — A single agent juggling retrieval,
query rewriting, and synthesis drops one of those responsibilities under
load. Specialization makes each failure mode independent and debuggable.

**Sequential handoff, not peer-to-peer** — Sub-agents don't talk to each
other. They only talk to the orchestrator via return values. This keeps the
flow linear and easy to trace.

**Query rewriting as a first-class step** — Putting query rewriting before
retrieval eliminates the vocabulary mismatch problem that caused Stage 3
to need multiple retrieval iterations. Better queries on the first attempt
reduces LLM calls and latency.

**Defensive tool argument parsing** — Mistral occasionally passes a list
instead of a string for the query argument. The execute_tool function now
coerces lists to strings before calling the vector store.

**When NOT to use multi-agent** — If your single agent is working reliably,
don't split it. Multi-agent adds LLM calls (cost + latency), more failure
points, and debugging complexity. We split here because we had a demonstrated
retrieval quality problem that specialization genuinely solves.

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

**Switch providers**

Edit `config.py`:

```python
PROVIDER = "anthropic"  # or "openai" or "ollama"
```

### What the orchestrator looks like at runtime

```
============================================================
Question: What is the rollback procedure for a bad deployment?
============================================================

[Step 1: Query Rewriter]
  [QueryRewriter] Rewriting: 'What is the rollback procedure for a bad deployment?'
  [QueryRewriter] Generated queries: ['revert failed deployment', 'rollback bad release steps', 'undo production deployment']

[Step 2: Retriever]
  [Retriever] Executing 3 queries
  [Retriever] retrieve_documents({'query': 'revert failed deployment'})
  [Retriever] retrieve_documents({'query': 'rollback bad release steps'})
  [Retriever] retrieve_documents({'query': 'undo production deployment'})
  [Retriever] Retrieved 3 result(s)

[Step 3: Synthesizer]
  [Synthesizer] Writing answer from retrieved context
  [Synthesizer] Done

[Final Answer]
Run 'make rollback ENV=prod' from the repo root. Page the on-call engineer
if error rates don't stabilize within 10 minutes.
(Source: Production Deployment Runbook)
```

### Known limitations at this stage

- Query rewriter occasionally returns malformed JSON (falls back to original question)
- Retriever sub-agent rarely calls `get_document` — tool description needs tuning
- No formal eval suite — correctness is verified manually by reading output
- No guardrails against prompt injection or hallucination under pressure
- Both addressed in Stage 5 (evals) and Stage 6 (guardrails)

### Concepts this stage teaches

- Orchestrator vs worker pattern — one coordinator, multiple specialists
- Shared state as a plain dict — the simplest multi-agent communication primitive
- Sequential handoff vs peer-to-peer agent communication
- Why specialization makes failure modes independent and debuggable
- When multi-agent is over-engineering vs genuinely necessary
- Defensive parsing of LLM tool arguments

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
Insert would fail with duplicate ID errors if called twice.

**Cosine distance → similarity score** — ChromaDB returns distance (0 = identical).
We convert to similarity (1 = identical) with `score = 1 - distance`.

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
│  Think → Act → Observe → Think  │
│       (max 3 iterations)        │
└─────────────────────────────────┘
          │              │
          ▼              ▼
  ┌──────────────┐  ┌─────────────────────┐
  │  LLM (chat)  │  │    Vector Store     │
  │    Mistral   │  │  numpy + cosine sim │
  └──────────────┘  └─────────────────────┘
          │
          ▼
  Answer + source citations
```

### Key design decisions

**Provider abstraction** — One config value (`PROVIDER`) switches between
Ollama (local), Anthropic, and OpenAI. Zero changes to agent logic required.

**Manual ReAct loop** — No LangGraph or LlamaIndex. The loop is a plain
while loop that appends to a messages list. This is exactly what every
framework abstracts.

**Chunking with overlap** — Documents are split into 400-character chunks
with 80-character overlap. Overlap prevents key facts from being cut at
chunk boundaries.

### Concepts this stage teaches

- ReAct loop mechanics (Reason + Act)
- Tool calling at the API level
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
| 4 | Multi-agent orchestration | ✅ Done |
| 5 | Eval harness | 🔜 Next |
| 6 | Guardrails + HITL | ⬜ Planned |
| 7 | Production redesign | ⬜ Planned |
| 8 | Observability + tracing | ⬜ Planned |
| 9 | Deployment | ⬜ Planned |
| 10 | Improvement loop | ⬜ Planned |