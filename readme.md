# Research Assistant Agent

A production-grade RAG agent built end-to-end across 10 stages.
Each stage is a separate commit — read the history to watch the system evolve.

---

## Stage 6 — Human-in-the-Loop & Guardrails

### What this stage builds
Three layers of protection around the agent pipeline: an input guardrail that
blocks prompt injection and flags off-topic requests, an output guardrail that
scores answer confidence, and a HITL approval gate that pauses execution and
waits for human review when confidence is low.

### What changed from Stage 5

| | Stage 5 | Stage 6 |
|--|---------|---------|
| Input validation | None — all questions passed through | Rules-based injection detection + off-topic flagging |
| Output validation | None — all answers returned directly | Confidence scoring based on retrieval quality |
| Human oversight | None | Interactive approval gate on low-confidence answers |
| Abstention trust | Agent decides | Output guardrail explicitly trusts correct abstentions |

### Architecture

```
User input
    │
    ▼
┌─────────────────┐
│ Input Guardrail │  blocks injection, flags off-topic
└─────────────────┘
    │ allowed
    ▼
┌──────────────────────────────────┐
│  Query Rewriter → Retriever      │
│  → Synthesizer (Stage 4 agents)  │
└──────────────────────────────────┘
    │
    ▼
┌──────────────────┐
│ Output Guardrail │  scores confidence from retrieval quality
└──────────────────┘
    │
    ├── high/medium confidence ──→ return answer directly
    │
    └── low confidence ──────────→ HITL gate
                                       │
                                  ┌────┴────┐
                              (a) approve  (r) reject  (e) edit
                                       │
                                  final answer
```

### Files

| File | Purpose |
|------|---------|
| `guardrails/__init__.py` | Package marker |
| `guardrails/input_guard.py` | Injection patterns + off-topic detection |
| `guardrails/output_guard.py` | Confidence scoring + hallucination flag |
| `guardrails/hitl.py` | Interactive approval gate — approve / reject / edit |
| `agents/orchestrator.py` | Updated — 5-step pipeline with guardrails wired in |

### The 3 guardrail layers

**Input Guardrail** — runs before the orchestrator sees anything. Hard-blocks
prompt injection attempts using regex patterns. Soft-flags off-topic questions
with a warning passed to the orchestrator. Returns immediately on injection —
no LLM calls made.

**Output Guardrail** — runs after the synthesizer. Parses relevance scores from
retrieved chunks, computes average, and classifies confidence as high / medium
/ low. Flags hallucination risk when the answer makes confident assertions
despite weak retrieval. Explicitly trusts correct abstentions regardless of
retrieval score.

**HITL Gate** — runs when output guardrail sets `needs_review=True`. Prints a
full review panel showing the question, confidence score, flags, and proposed
answer. Waits for human input: approve passes the answer through, reject
returns a safe fallback, edit prompts for a replacement answer.

### Key design decisions

**Rules-based injection detection** — regex patterns catch 80% of real-world
attacks with zero latency and zero cost. LLM-based detection catches more
creative attacks but adds 1-3 seconds per request. Rules-based is the right
default; LLM-based is the production upgrade.

**Abstention always trusted** — when the agent says "I could not find an
answer", the output guardrail classifies this as high confidence regardless
of retrieval score. Correct abstention is always the right answer on
unanswerable questions. Never send a correct abstention to human review.

**Confidence from retrieval score, not LLM** — we parse relevance scores
directly from the formatted chunk string. This is deterministic and free.
An LLM-based confidence scorer would add cost and latency for marginal gain.

**Confident assertion + weak retrieval = hallucination flag** — the most
dangerous failure mode is a confident-sounding wrong answer from marginal
context. The output guardrail detects this pattern explicitly and routes to
human review.

### How to run

```bash
python main.py
```

Injection attempt:
```
[Step 0: Input Guardrail]
  [InputGuard] BLOCKED — injection pattern matched: 'ignore (previous|prior|all|your) instructions'
  [Orchestrator] Input blocked. Returning safe message.
```

Low-confidence answer (triggers HITL):
```
[Step 4: Output Guardrail]
  [OutputGuard] ⚠️  confidence=low, score=0.43, review=True
  [OutputGuard]    flag: Confident assertion with low retrieval score (0.43)

============================================================
⚠️  HUMAN REVIEW REQUIRED
============================================================
Question:   ...
Confidence: LOW (score: 0.43)
Proposed answer: ...
============================================================
[HITL] Decision — (a) approve  (r) reject  (e) edit:
```

### Advanced RAG patterns (context)

The image below shows 6 RAG variants. Here is how they map to what we built:

| Pattern | What it is | Where it appears in this project |
|---------|-----------|----------------------------------|
| Hybrid RAG | Semantic + keyword search combined | Stage 3 upgrade — add BM25 alongside ChromaDB |
| Graph RAG | Knowledge graph of entity relationships | Future extension |
| Agentic RAG | Agents choose tools and retrieval paths dynamically | Stage 4 — our orchestrator pattern |
| Corrective RAG | Validates and repairs weak retrieval before generation | Stage 6 — our output guardrail |
| Multimodal RAG | Retrieves across PDFs, images, tables | Stage 3 upgrade — real file loader |
| Self-RAG | Model critiques its own retrieval before responding | Stage 6 — automated version of our output guardrail |

### Known limitations at this stage

- Injection detection is rules-based — creative attacks that avoid known
  phrases will pass through (mitigated by output guardrail catching
  hallucinated answers downstream)
- Confidence thresholds (0.65 high, 0.50 low) are hand-tuned — production
  systems should calibrate these against eval results
- HITL gate is synchronous CLI — production would use an async review queue
  (Slack message, email, dashboard) that doesn't block the request thread
- No rate limiting on HITL reviews — a flood of low-confidence answers
  would overwhelm a human reviewer

### Concepts this stage teaches

- Defense in depth — multiple independent layers catch different failure modes
- Rules-based vs LLM-based guardrails — when each is appropriate
- Confidence scoring from retrieval signals — deterministic and free
- Why abstention should always be trusted — the logic behind the design
- HITL as a safety valve, not a crutch — when to interrupt vs proceed

---

## Stage 5 — Reliability & Evals

### What this stage builds
An eval harness with 13 test cases, three levels of automated scoring, and
LLM-as-judge for non-deterministic answer evaluation.

### Eval levels
- **L2 Answer** — LLM-as-judge scores against reference answers
- **L3 Abstention** — marker detection for "I don't know" responses
- **Citation** — checks source document citations

### How to run evals
```bash
python main.py --eval
```

### Concepts this stage teaches
- LLM-as-judge with tight rubrics
- Abstention accuracy as the most important production metric
- Regression harness — run after every change
- Fail closed on parse errors

---

## Stage 4 — Multi-Agent Orchestration

### What this stage builds
Orchestrator + 3 specialized sub-agents: Query Rewriter, Retriever, Synthesizer.

### The 3 sub-agents
- **Query Rewriter** — rewrites question into 2-3 optimized search queries
- **Retriever** — executes tool calls, decides retrieve vs get_document
- **Synthesizer** — writes grounded answer with citations

### Concepts this stage teaches
- Orchestrator vs worker pattern
- Sequential handoff vs peer-to-peer
- When NOT to use multi-agent
- Defensive parsing of LLM tool arguments

---

## Stage 3 — Tools & Memory

### What this stage builds
ChromaDB persistent index, file loader, 3-tool architecture.

### Key design decisions
- Build once, reuse forever — skip rebuild if index exists
- Upsert not insert — idempotent index builds
- Supply own embeddings — keeps provider abstraction intact

### Concepts this stage teaches
- Why in-memory vector stores break in production
- ChromaDB persistent collections
- Tool description quality affects tool selection

---

## Stage 2 — Minimal Working Agent (MVP)

### What this stage builds
ReAct loop by hand, in-memory vector store, single retrieval tool.

### Key design decisions
- Provider abstraction — one config value switches Ollama/Anthropic/OpenAI
- Manual ReAct loop — no frameworks, every line visible
- Chunking with overlap — 400 chars + 80 char overlap

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
| 7 | Production redesign | 🔜 Next |
| 8 | Observability + tracing | ⬜ Planned |
| 9 | Deployment | ⬜ Planned |
| 10 | Improvement loop | ⬜ Planned |