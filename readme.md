# Research Assistant Agent

A production-grade RAG agent built end-to-end across 10 stages.
Each stage is a separate commit — read the history to watch the system evolve.

---

## Stage 7 — System Design for Production

### What this stage builds
Three production engineering upgrades: async parallel retrieval so all queries
fire concurrently, streaming synthesis so the user sees the first token in ~1s
instead of waiting for the full answer, and model routing so simple questions
use a cheap fast model while complex questions use a capable model.

### What changed from Stage 6

| | Stage 6 | Stage 7 |
|--|---------|---------|
| Retrieval execution | Sequential — query 1 → query 2 → query 3 | Parallel — all queries fire concurrently |
| Synthesis output | Full answer returned at once | Tokens streamed as generated |
| Model selection | Same model for every question | Routed — fast model for simple, capable for complex |
| Latency profile | Sequential I/O bottleneck | I/O-bound work parallelized |

### Architecture

```
Query Rewriter              ~30s  ──┐
                                    │ rewriter must finish first
                                    ▼
Retrieve query 1  ──┐
Retrieve query 2  ──┼── asyncio.gather()  ~20s  (all 3 concurrently)
Retrieve query 3  ──┘
                                    │
                                    ▼
              ┌─────────────────────────────┐
              │  Model Router               │
              │  simple question → FAST     │
              │  complex question → CAPABLE │
              └─────────────────────────────┘
                                    │
                                    ▼
              Synthesizer (streaming)       ~40s
              tokens appear immediately ────────→ user sees output
```

### Files changed

| File | What changed |
|------|-------------|
| `config.py` | Added FAST_MODEL, CAPABLE_MODEL, COMPLEX_QUERY_KEYWORDS, STREAM_ENABLED |
| `agents/retriever.py` | Rewritten with asyncio — parallel query execution via asyncio.gather |
| `agents/synthesizer.py` | Added streaming, model routing, Anthropic streaming support |

### Key concepts

**Async parallel retrieval** — `asyncio.gather()` runs all query coroutines
concurrently. On cloud providers where each API call goes to a different server,
3 queries that each take 1s run in ~1s total instead of ~3s total. On local
Ollama, parallelism doesn't reduce wall-clock time because the local process
can only run one inference at a time — the architecture is correct, the
hardware is the constraint.

```python
# Before: sequential
for query in queries:
    result = retrieve(query)    # waits for each

# After: parallel
tasks   = [_execute_single_query(q) for q in queries]
results = await asyncio.gather(*tasks)  # all fire at once
```

**run_in_executor pattern** — the OpenAI client is synchronous. To use it
inside an async function without blocking the event loop, we wrap it in
`loop.run_in_executor(None, lambda: sync_call())`. This moves the blocking
call to a thread pool so other coroutines can run while waiting.

```python
result = await loop.run_in_executor(
    None,                          # default thread pool
    lambda: _sync_retrieve(query)  # blocking call runs in thread
)
```

**Streaming** — instead of waiting for the full answer, we pass `stream=True`
to the chat completions API and iterate over chunks. Each chunk contains a
token. We print it immediately with `flush=True` so the user sees output
start in ~1 second.

```python
stream = client.chat.completions.create(
    model=model, messages=messages, stream=True
)
for chunk in stream:
    token = chunk.choices[0].delta.content
    if token:
        print(token, end="", flush=True)  # immediate output
```

**Model routing** — two signals determine which model handles synthesis.
If either fires, route to CAPABLE_MODEL; otherwise use FAST_MODEL.

```python
# Signal 1: complexity keywords in question
has_complex_keyword = any(kw in question.lower() for kw in COMPLEX_QUERY_KEYWORDS)

# Signal 2: answer requires chunks from multiple source documents
sources      = set(re.findall(r"Source:\s*([^\n(]+)", retrieved_context))
is_multi_doc = len(sources) >= 2
```

**Exception isolation** — if one parallel query fails, the others continue.
`asyncio.gather(*tasks, return_exceptions=True)` returns exceptions as values
instead of raising them. We filter them out and log them without crashing.

```python
results = await asyncio.gather(*tasks, return_exceptions=True)
for result in results:
    if isinstance(result, Exception):
        print(f"Query failed: {result}")   # log and continue
    else:
        all_results.append(result)
```

### Latency analysis

| Provider | Before Stage 7 | After Stage 7 | Note |
|----------|---------------|---------------|------|
| Local Ollama | 90-200s | 90-200s | Sequential at hardware level — no change |
| OpenAI GPT-4o | ~9s | ~3s | 3 parallel 1s calls instead of 3 sequential |
| Anthropic Claude | ~8s | ~2.5s | Same parallelism benefit |

The architecture is production-correct. The local constraint is hardware, not design.

### Production gotchas

**asyncio + sync libraries** — the OpenAI client is synchronous. Calling it
directly inside an async function blocks the entire event loop. Always use
`run_in_executor` to move sync I/O to a thread pool.

**asyncio.run() in a running loop** — calling `asyncio.run()` inside an
already-running event loop raises a RuntimeError. If your orchestrator ever
becomes async, switch to `await _retrieve_async()` directly instead of
`asyncio.run()`.

**Streaming and guardrails** — streaming returns tokens as they arrive.
The output guardrail runs after synthesis completes, not during streaming.
This means the user might see tokens before the guardrail has a chance to
flag the answer. In production, buffer the stream and run guardrails before
releasing to the user if safety is critical.

**Model routing compound failures** — if the rewriter fails and falls back
to the original question as a single long query, retrieval returns fewer
chunks, which may cause the router to select FAST_MODEL even for a complex
question. Each component failure can cascade. This is why trajectory evals
(Stage 5) matter — they catch multi-component failures that unit evals miss.

### How to run

```bash
python main.py
```

Streaming output looks like:
```
[Step 3: Synthesizer]
  [Synthesizer] Routing → FAST model
  [Synthesizer] Model: mistral:latest | Stream: True
  [Synthesizer] Streaming: Full-time employees accrue 15 days of paid time
  off (PTO) per calendar year. (Source: PTO & Leave Policy)
```

Disable streaming in `config.py`:
```python
STREAM_ENABLED = False
```

Switch to cloud providers in `config.py`:
```python
PROVIDER      = "anthropic"
FAST_MODEL    = "claude-haiku-3"
CAPABLE_MODEL = "claude-sonnet-4-5"
```

### Concepts this stage teaches

- asyncio.gather() for concurrent I/O-bound work
- run_in_executor pattern for using sync libraries in async code
- Streaming at the API level — stream=True and chunk iteration
- Model routing — when to use cheap vs capable models
- Exception isolation in parallel execution
- Why parallelism helps cloud providers but not local models

---

## Stage 6 — Human-in-the-Loop & Guardrails

### What this stage builds
Input guardrail (injection detection), output confidence scoring, interactive
HITL approval gate.

### The 3 layers
- **Input Guardrail** — regex injection detection, off-topic flagging
- **Output Guardrail** — confidence scoring from retrieval quality
- **HITL Gate** — interactive approve / reject / edit on low-confidence answers

### Key design decisions
- Rules-based injection detection — zero latency, zero cost
- Abstention always trusted — never send correct "I don't know" to review
- Confident assertion + weak retrieval = hallucination flag

### Concepts this stage teaches
- Defense in depth — independent layers catch different failures
- Rules-based vs LLM-based guardrails
- Confidence scoring from retrieval signals
- HITL as a safety valve, not a crutch

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

---

## Stage 3 — Tools & Memory

### What this stage builds
ChromaDB persistent index, file loader, 3-tool architecture.

---

## Stage 2 — Minimal Working Agent (MVP)

### What this stage builds
ReAct loop by hand, in-memory vector store, single retrieval tool.

### How to run
```bash
pip install openai anthropic numpy chromadb python-dotenv
ollama pull mistral
ollama pull nomic-embed-text
python main.py           # run agent
python main.py --eval    # run eval suite
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
| 8 | Observability + tracing | 🔜 Next |
| 9 | Deployment | ⬜ Planned |
| 10 | Improvement loop | ⬜ Planned |