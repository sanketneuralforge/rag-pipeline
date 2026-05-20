# Research Assistant Agent

A production-grade RAG agent built end-to-end across 10 stages.
Each stage is a separate commit — read the history to watch the system evolve.

---

## Stage 5 — Reliability & Evals

### What this stage builds
An eval harness with 13 test cases, three levels of automated scoring, and
LLM-as-judge for non-deterministic answer evaluation. Establishes a baseline
before any production changes are made.

### What changed from Stage 4

| | Stage 4 | Stage 5 |
|--|---------|---------|
| Correctness verification | Read terminal output manually | Automated scoring across 13 test cases |
| Answer quality | Subjective | LLM-as-judge with rubric |
| Abstention | Checked by eye | Automated marker detection |
| Regression detection | None | Run `--eval` flag after any change |

### Eval levels

**Level 2 — Answer eval** — LLM-as-judge scores the agent's answer against a
reference answer. Handles non-deterministic outputs where exact string matching
fails. A second LLM reads question + reference + agent answer and returns
`{"score": 0|1, "reason": "..."}`.

**Level 3 — Abstention eval** — Checks whether the agent correctly says
"I don't know" on unanswerable questions. Scans for abstention markers in the
answer text. This is the most important eval for production trust.

**Citation eval** — Checks whether the agent cited the expected source document
in its answer. Runs on all answerable questions.

### Baseline results (Ollama + Mistral, local hardware)

> Fill in your actual numbers after the full eval run completes.

```
======================================================
EVAL RESULTS
======================================================
Overall:     __/13 passed  (__%)
L2 Answer:   __/10 correct (__%)    target: ≥ 80%
L3 Abstain:  __/3  correct (__%)    target: ≥ 90%
Citation:    __/10 cited   (__%)    target: ≥ 95%
Avg latency: __s                    target: < 4s
======================================================
```

> Note: Latency on local Ollama + Mistral is 90-200s per question due to
> three sequential LLM calls. This is a hardware constraint, not an
> architecture flaw. Addressed in Stage 7 with parallel async execution
> and cloud model routing.

### Files

| File | Purpose |
|------|---------|
| `evals/__init__.py` | Package marker |
| `evals/dataset.py` | 13 test cases — 10 answerable, 3 unanswerable |
| `evals/judge.py` | LLM-as-judge + abstention + citation scorers |
| `evals/runner.py` | Runs all evals, prints per-case results and summary |
| `main.py` | Updated — `--eval` flag triggers eval suite |

### How to run evals

```bash
python main.py --eval
```

Output per case:
```
[1/13] pto-001: How many PTO days do full-time employees get per year?
  Latency:   203s
  Answer:    Full-time employees accrue 15 days of paid time off per calendar year...
  L2 Answer: ✅ Answer contains correct key facts
  Citation:  ✅ Cited 'PTO & Leave Policy'
```

### Key design decisions

**LLM-as-judge over string matching** — Agent answers are non-deterministic.
"Employees get 15 PTO days yearly" and "Full-time employees accrue 15 days of
paid time off per calendar year" are the same answer. String matching fails
both. LLM-as-judge understands semantic equivalence.

**Tight scoring rubric** — The judge prompt defines exact criteria: score 1
if key facts are present even if worded differently, score 0 if facts are
missing, wrong, or hallucinated. Tight rubrics reduce judge bias.

**Lowercase key normalization** — Mistral capitalizes JSON keys (`"Score"`
instead of `"score"`). The parser normalizes all keys to lowercase before
reading them. Always normalize LLM-generated structured output before parsing.

**Fail closed on parse errors** — If the judge returns unparseable output,
we score 0, never 1. Silently passing a bad answer is worse than a false
failure.

**Abstention markers over LLM judge** — Checking for abstention phrases
("could not find", "cannot find", etc.) is faster, cheaper, and more
reliable than asking an LLM to judge it. Use deterministic checks wherever
possible, LLM judge only when semantics matter.

**Success criteria set in Stage 1** — The eval targets (80% answer accuracy,
90% abstention, 95% citation) were defined before we wrote a line of code.
Evals verify we hit the targets we designed for, not targets we reverse-
engineered from the results.

### Interview angle

This stage prepares you to answer:
- "How do you evaluate a non-deterministic system?"
- "What is LLM-as-judge and what are its failure modes?"
- "How do you prevent regressions when you change a prompt?"
- "What is the difference between unit evals, trajectory evals, and end-to-end evals?"

### Known limitations at this stage

- No trajectory evals — we score final answers but not whether the agent
  took the right path (e.g. called the right tools in the right order)
- Judge is the same model as the agent — ideally use a stronger model as
  judge (GPT-4o or Claude) for more reliable scoring
- 13 test cases is a minimum viable dataset — production systems need 100+
- Latency is 90-200s on local Ollama — addressed in Stage 7

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

### The 3 sub-agents

**Query Rewriter** — Rewrites question into 2-3 optimized search queries using
different vocabulary. Fixes vocabulary mismatch between user language and
document language.

**Retriever** — Executes tool calls against ChromaDB. Decides whether to use
`retrieve_documents` or `get_document`. Returns all retrieved chunks.

**Synthesizer** — Writes grounded answer with citations. Abstains correctly
when context is insufficient.

### Key design decisions

**Specialization over generalization** — A single agent juggling retrieval,
query rewriting, and synthesis drops one responsibility under load.
Specialization makes each failure mode independent and debuggable.

**Sequential handoff, not peer-to-peer** — Sub-agents only talk to the
orchestrator via return values. Flow is linear and easy to trace.

**When NOT to use multi-agent** — If your single agent works reliably, don't
split it. Multi-agent adds LLM calls (cost + latency), more failure points,
and debugging complexity.

### Concepts this stage teaches

- Orchestrator vs worker pattern
- Shared state as a plain dict
- Sequential handoff vs peer-to-peer communication
- When multi-agent is over-engineering vs genuinely necessary
- Defensive parsing of LLM tool arguments

---

## Stage 3 — Tools & Memory

### What this stage builds
Replaces the in-memory numpy vector store with ChromaDB for persistent storage.
Adds a real file loader. Extends the agent from 1 tool to 3 tools.

### What changed from Stage 2

| | Stage 2 | Stage 3 |
|--|---------|---------|
| Vector store | numpy matrix in RAM | ChromaDB on disk |
| Index lifetime | Rebuilt every startup | Built once, reused forever |
| Corpus | Hardcoded inline strings | `.txt` files loaded from `docs/` |
| Tools | `retrieve_documents` only | + `list_documents` + `get_document` |

### Key design decisions

**Build once, reuse forever** — `VectorStore.build()` skips if collection
already exists. Zero embedding API calls on subsequent startups.

**Upsert not insert** — Safe to call multiple times. Insert fails on
duplicate IDs.

**Cosine distance → similarity** — ChromaDB returns distance (0 = identical).
Converted to similarity with `score = 1 - distance`.

### Concepts this stage teaches

- Why in-memory vector stores break in production
- ChromaDB persistent collections
- Upsert vs insert for idempotent index builds
- Tool description quality affects tool selection

---

## Stage 2 — Minimal Working Agent (MVP)

### What this stage builds
A fully working RAG agent from scratch using raw API calls and no frameworks.
The core ReAct loop is implemented by hand so every abstraction is visible.

### Key design decisions

**Provider abstraction** — One config value (`PROVIDER`) switches between
Ollama, Anthropic, and OpenAI. Zero changes to agent logic.

**Manual ReAct loop** — Plain while loop appending to a messages list.
This is exactly what every framework abstracts.

**Chunking with overlap** — 400-character chunks with 80-character overlap.
Prevents key facts from being cut at chunk boundaries.

### How to run

```bash
# Install dependencies
pip install openai anthropic numpy chromadb python-dotenv

# Pull Ollama models
ollama pull mistral
ollama pull nomic-embed-text

# Run agent
python main.py

# Run eval suite
python main.py --eval
```

### Concepts this stage teaches

- ReAct loop mechanics
- Tool calling at the API level
- Chunking and retrieval precision
- Cosine similarity vs euclidean distance
- Provider abstraction pattern

---

## Stages

| Stage | What it builds | Status |
|-------|----------------|--------|
| 1 | Problem framing + system design doc | ✅ Done |
| 2 | MVP ReAct agent + in-memory RAG | ✅ Done |
| 3 | ChromaDB + persistent index + 3 tools | ✅ Done |
| 4 | Multi-agent orchestration | ✅ Done |
| 5 | Eval harness | ✅ Done |
| 6 | Guardrails + HITL | 🔜 Next |
| 7 | Production redesign | ⬜ Planned |
| 8 | Observability + tracing | ⬜ Planned |
| 9 | Deployment | ⬜ Planned |
| 10 | Improvement loop | ⬜ Planned |