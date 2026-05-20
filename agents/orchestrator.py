# agents/orchestrator.py

from agents.query_rewriter import rewrite
from agents.retriever import retrieve
from agents.synthesizer import synthesize


def run(question: str) -> str:
    """
    Orchestrates the full pipeline:
      1. Query Rewriter  — rewrites question into optimized search queries
      2. Retriever       — executes tool calls, returns relevant chunks
      3. Synthesizer     — writes grounded answer with citations

    Shared state is a plain dict passed forward at each step.
    No message queues, no async, no frameworks — sequential handoff.
    """
    print(f"\n{'='*60}")
    print(f"Question: {question}")
    print(f"{'='*60}")

    # Shared state — grows as each agent contributes
    state = {
        "question":         question,
        "rewritten_queries": [],
        "retrieved_chunks":  "",
        "final_answer":      "",
    }

    # Step 1 — Query Rewriter
    print("\n[Step 1: Query Rewriter]")
    state["rewritten_queries"] = rewrite(question)

    # Step 2 — Retriever
    print("\n[Step 2: Retriever]")
    state["retrieved_chunks"] = retrieve(
        state["question"],
        state["rewritten_queries"],
    )

    # Step 3 — Synthesizer
    print("\n[Step 3: Synthesizer]")
    state["final_answer"] = synthesize(
        state["question"],
        state["retrieved_chunks"],
    )

    print(f"\n[Final Answer]\n{state['final_answer']}")
    return state["final_answer"]