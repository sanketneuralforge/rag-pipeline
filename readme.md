# Research Assistant Agent

A production-grade RAG agent built end-to-end across 10 stages.
Each stage is a separate commit — read the history to watch the system evolve.

---

## Stage 9 — Deployment

### What this stage builds
A FastAPI server that exposes the agent as an HTTP API. Four endpoints:
`POST /ask` runs the full agent pipeline, `GET /health` is a liveness check,
`GET /metrics` returns aggregate run metrics as JSON, and `GET /traces/{run_id}`
fetches a complete trace for debugging.

### What changed from Stage 8

| | Stage 8 | Stage 9 |
|--|---------|---------|
| Interface | Terminal only | HTTP API over FastAPI |
| Input validation | Manual string checks | Pydantic models with automatic 422 responses |
| Response format | Terminal print | Structured JSON with run_id, confidence, spans |
| Debuggability | Read log files manually | Fetch any run by ID via API |
| Observability | Terminal dashboard | Machine-readable JSON metrics endpoint |

### API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness check — returns status + index_ready flag |
| `POST` | `/ask` | Run the agent — returns answer, confidence, spans |
| `GET` | `/metrics` | Aggregate metrics across recent runs |
| `GET` | `/traces` | List recent run IDs and status |
| `GET` | `/traces/{run_id}` | Full trace for a specific run |
| `GET` | `/docs` | Auto-generated Swagger UI |

### How to run

```bash
# Install dependencies
pip install fastapi uvicorn pydantic

# Start the server
python api.py
```

Server starts at `http://localhost:8000`. Visit `http://localhost:8000/docs`
for the interactive Swagger UI.

### Example requests

**Ask a question:**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How many PTO days do employees get per year?"}'
```

**Response:**
```json
{
  "run_id": "88e08fcc",
  "question": "How many PTO days do employees get per year?",
  "answer": "Full-time employees accrue 15 days of paid time off per calendar year. (Source: PTO & Leave Policy)",
  "confidence": "medium",
  "latency_s": 132.964,
  "spans": [
    { "name": "input_guard",    "duration_s": 0.001, "status": "success" },
    { "name": "query_rewriter", "duration_s": 35.8,  "status": "success" },
    { "name": "retriever",      "duration_s": 42.4,  "status": "success" },
    { "name": "synthesizer",    "duration_s": 54.7,  "status": "success" },
    { "name": "output_guard",   "duration_s": 0.007, "status": "success" },
    { "name": "hitl",           "duration_s": 0.0,   "status": "success" }
  ]
}
```

**Health check:**
```bash
curl http://localhost:8000/health
# {"status": "ok", "version": "1.0.0", "index_ready": true}
```

**Fetch a trace:**
```bash
curl http://localhost:8000/traces/88e08fcc
```

**Validation error (question too short):**
```bash
curl -X POST http://localhost:8000/ask \
  -d '{"question": "hi"}'
# 422 Unprocessable Entity — "String should have at least 3 characters"
```

### Key design decisions

**Pydantic request validation** — `AskRequest` enforces `min_length=3` and
`max_length=1000`. FastAPI automatically returns a 422 with a clear error
message on invalid input. No manual validation code needed.

**Structured JSON response** — every `/ask` response includes `run_id`,
`confidence`, `latency_s`, and per-span timing. Clients get enough information
to display confidence indicators, log slow queries, and link to traces.

**Trace-per-request** — every API call writes a trace file. The `/traces/{run_id}`
endpoint retrieves it by ID. This means any failed production request is
permanently debuggable — not just the ones you happened to be watching.

**CORS middleware** — allows browser clients to call the API directly. Set
`allow_origins` to specific domains in production rather than `"*"`.

**Reload mode** — `uvicorn.run(..., reload=True)` restarts the server on
file changes during development. Remove `reload=True` in production.

### Production gotchas

**Streaming vs JSON response** — our synthesizer streams tokens to the
terminal. Over HTTP, streaming requires Server-Sent Events (SSE) or
WebSockets. The current `/ask` endpoint buffers the full answer before
responding. For streaming HTTP responses, use FastAPI's `StreamingResponse`
with an async generator.

**Blocking the event loop** — the agent pipeline is synchronous (Ollama
calls block). In production with concurrent requests, wrap `run()` in
`asyncio.run_in_executor` so the FastAPI event loop isn't blocked while
the agent processes. Otherwise request 2 waits for request 1 to finish
before starting.

**HITL over HTTP** — the HITL gate currently prompts the terminal for
input. Over HTTP this breaks. In production, replace the CLI prompt with
an async review queue: write the pending answer to a database, send a
Slack/email notification, and expose a `POST /review/{run_id}` endpoint
for the human to approve or reject.

---

## Stage 8 — Observability & Monitoring

### What this stage builds
Span-level tracing that records every step of every agent run, metrics
aggregation across runs, and a terminal dashboard showing completion rate,
latency p50/p90, retrieval quality, and per-span timing breakdowns.

### What changed from Stage 7

| | Stage 7 | Stage 8 |
|--|---------|---------|
| Run visibility | Terminal output only | Structured JSON trace per run |
| Debugging | Read scrolling logs | Fetch trace by run_id |
| Performance data | None | p50/p90 latency, per-span breakdown |
| Failure tracking | Crash and read traceback | Error spans with root cause |
| History | Lost on process exit | Persisted to `traces/` directory |

### Files

| File | Purpose |
|------|---------|
| `observability/__init__.py` | Package marker |
| `observability/tracer.py` | Span + Trace data structures, JSON persistence |
| `observability/metrics.py` | Aggregates across runs — completion, latency, relevance |
| `observability/dashboard.py` | Terminal dashboard with alerts |
| `traces/` | Auto-created — one JSON file per run |

### Dashboard output

```
==============================================================
  AGENT OBSERVABILITY DASHBOARD  —  last 5 runs
==============================================================

  AGGREGATE METRICS
  ──────────────────────────────────────────────────────────
  Total runs:        5
  Completion rate:   100%
  Error rate:        0%
  Abstention rate:   40%
  Latency p50:       117s
  Latency p90:       132s
  Avg relevance:     0.587
  HITL rate:         0%

  AVERAGE SPAN LATENCY
  ──────────────────────────────────────────────────────────
  synthesizer            56.317s  ████████████████████████████
  retriever              42.060s  █████████████████████
  query_rewriter         23.191s  ████████████
  output_guard            0.005s
  input_guard             0.001s
  hitl                    0.000s

  ALERTS
  ──────────────────────────────────────────────────────────
  ⚠️  p90 latency 132s exceeds 4s target
==============================================================
```

### Key design decisions

**One JSON file per run** — each trace is written to `traces/{run_id}.json`
on completion. Files accumulate over time and are queryable by run_id. Simple,
no database required, works on any filesystem.

**Span as context** — each span captures name, start time, end time, status,
metadata, and error. The orchestrator creates a span at the start of each step
and calls `span.finish()` or `span.fail()` at the end. Error spans include
the exception message so failures are self-documenting.

**Latency computed from timestamps** — `duration_s` is computed from
`end_time - start_time`. If `duration_s` is missing from a trace file, the
metrics layer falls back to computing it from raw timestamps. Defensive
reading handles traces written by older code versions.

**p50 and p90, not average** — average latency hides outliers. p90 tells you
what 90% of users experience. p50 is the median. A system with p50=2s and
p90=120s has a serious tail latency problem that the average would obscure.

**Alert thresholds** — four production alerts are defined: error rate > 10%,
p90 latency > 4s, avg relevance < 0.55, HITL rate > 30%. These map directly
to the success criteria defined in Stage 1. The dashboard flags when we fall
below our own targets.

### Production metrics every RAG system should track

| Metric | Why it matters |
|--------|---------------|
| Task completion rate | Did the agent produce an answer at all? |
| Abstention rate | How often does it admit uncertainty? |
| Error rate | How often do spans fail? |
| Latency p50/p90 | What do most users experience? |
| Avg retrieval relevance | Is the vector store returning good chunks? |
| HITL rate | How often does a human need to intervene? |

---

## Stage 7 — Production System Design

### What this stage builds
Async parallel retrieval, streaming synthesis, model routing.

### Key concepts
- `asyncio.gather()` runs all retrieval queries concurrently
- `run_in_executor` wraps sync OpenAI client for async use
- `stream=True` streams tokens as generated
- Model routing: keywords + multi-doc detection → FAST vs CAPABLE model

### Latency impact
On local Ollama: no change (hardware bottleneck).
On cloud providers: retrieval drops from N×latency to ~1×latency.

---

## Stage 6 — Human-in-the-Loop & Guardrails

### What this stage builds
Input guardrail (injection detection), output confidence scoring, interactive
HITL approval gate (approve / reject / edit).

### Key design decisions
- Rules-based injection: zero latency, catches 80% of attacks
- Abstention always trusted: never send "I don't know" to human review
- Confident assertion + weak retrieval = hallucination flag → HITL

---

## Stage 5 — Reliability & Evals

### What this stage builds
Eval harness — 13 test cases, LLM-as-judge, abstention scoring, regression runner.

```bash
python main.py --eval
```

---

## Stage 4 — Multi-Agent Orchestration

### What this stage builds
Orchestrator + Query Rewriter + Retriever + Synthesizer sub-agents.
Sequential handoff via shared state dict. No message queues, no frameworks.

---

## Stage 3 — Tools & Memory

### What this stage builds
ChromaDB persistent index, file loader, 3-tool architecture.
Build once, reuse forever. Upsert not insert.

---

## Stage 2 — Minimal Working Agent (MVP)

### What this stage builds
ReAct loop by hand, in-memory vector store, single retrieval tool.
Provider abstraction — one config change switches Ollama/Anthropic/OpenAI.

### How to run

```bash
# Install dependencies
pip install openai anthropic numpy chromadb python-dotenv fastapi uvicorn pydantic

# Pull Ollama models
ollama pull mistral
ollama pull nomic-embed-text

# Run agent in terminal
python main.py

# Run eval suite
python main.py --eval

# View dashboard only
python main.py --dashboard

# Start API server
python api.py
```

---

## Stages

| Stage | What it builds | Status |
|-------|----------------|--------|
| 1 | Problem framing + system design doc | ✅ Done |
| 2 | MVP ReAct agent + in-memory RAG | ✅ Done |
| 3 | ChromaDB + persistent index + 3 tools | ✅ Done |
| 4 | Multi-agent orchestration | ✅ Done |
| 5 | Eval harness | ✅ Done |
| 6 | Guardrails + HITL | ✅ Done |
| 7 | Production redesign | ✅ Done |
| 8 | Observability + tracing | ✅ Done |
| 9 | Deployment | ✅ Done |
| 10 | Improvement loop | 🔜 Next |