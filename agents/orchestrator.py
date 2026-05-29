# agents/orchestrator.py

from agents.query_rewriter import rewrite
from agents.retriever import retrieve
from agents.synthesizer import synthesize
from guardrails.input_guard import check as input_check
from guardrails.output_guard import check as output_check
from guardrails.hitl import review


def run(question: str) -> str:
    print(f"\n{'='*60}")
    print(f"Question: {question}")
    print(f"{'='*60}")

    # ── Step 0: Input guardrail ─────────────────────────────────────────────
    print("\n[Step 0: Input Guardrail]")
    input_result = input_check(question)

    if not input_result.allowed:
        blocked_msg = (
            "I cannot process this request. "
            f"Reason: {input_result.reason}"
        )
        print(f"  [Orchestrator] Input blocked. Returning safe message.")
        return blocked_msg

    if input_result.warning:
        print(f"  [Orchestrator] Warning noted: {input_result.warning}")

    # ── Step 1: Query Rewriter ──────────────────────────────────────────────
    print("\n[Step 1: Query Rewriter]")
    rewritten_queries = rewrite(question)

    # ── Step 2: Retriever ───────────────────────────────────────────────────
    print("\n[Step 2: Retriever]")
    retrieved_chunks = retrieve(question, rewritten_queries)

    # ── Step 3: Synthesizer ─────────────────────────────────────────────────
    print("\n[Step 3: Synthesizer]")
    answer = synthesize(question, retrieved_chunks)

    # ── Step 4: Output guardrail ────────────────────────────────────────────
    print("\n[Step 4: Output Guardrail]")
    output_result = output_check(answer, retrieved_chunks)

    # ── Step 5: HITL gate ───────────────────────────────────────────────────
    final_answer = review(question, answer, output_result)

    print(f"\n[Final Answer]\n{final_answer}")
    return final_answer