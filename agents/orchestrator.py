# agents/orchestrator.py

import re
from agents.query_rewriter import rewrite
from agents.retriever import retrieve
from agents.synthesizer import synthesize
from guardrails.input_guard import check as input_check
from guardrails.output_guard import check as output_check
from guardrails.hitl import review
from observability.tracer import tracer


def run(question: str) -> str:
    # ── Start trace ─────────────────────────────────────────────────────────
    trace = tracer.start_run(question)

    print(f"\n{'='*60}")
    print(f"Question: {question}")
    print(f"{'='*60}")

    # ── Step 0: Input guardrail ─────────────────────────────────────────────
    print("\n[Step 0: Input Guardrail]")
    span = tracer.start_span("input_guard")
    input_result = input_check(question)

    if not input_result.allowed:
        span.fail(error=input_result.reason)
        tracer.finish_run(
            status="blocked",
            final_answer="blocked",
            block_reason=input_result.reason,
        )
        return f"I cannot process this request. Reason: {input_result.reason}"

    span.finish(status="success", warning=input_result.warning)

    # ── Step 1: Query Rewriter ──────────────────────────────────────────────
    print("\n[Step 1: Query Rewriter]")
    span = tracer.start_span("query_rewriter")
    try:
        rewritten_queries = rewrite(question)
        span.finish(status="success", queries=rewritten_queries)
    except Exception as e:
        span.fail(error=str(e))
        rewritten_queries = [question]

    # ── Step 2: Retriever ───────────────────────────────────────────────────
    print("\n[Step 2: Retriever]")
    span = tracer.start_span("retriever")
    try:
        retrieved_chunks = retrieve(question, rewritten_queries)

        # Extract relevance scores for metrics
        scores     = re.findall(r"relevance:\s*([\d.]+)", retrieved_chunks)
        avg_rel    = round(sum(float(s) for s in scores) / len(scores), 3) if scores else 0.5
        span.finish(status="success", results=len(scores), avg_relevance=avg_rel)
    except Exception as e:
        span.fail(error=str(e))
        retrieved_chunks = ""

    # ── Step 3: Synthesizer ─────────────────────────────────────────────────
    print("\n[Step 3: Synthesizer]")
    span = tracer.start_span("synthesizer")
    try:
        answer = synthesize(question, retrieved_chunks)
        span.finish(status="success", answer_length=len(answer))
    except Exception as e:
        span.fail(error=str(e))
        answer = "I encountered an error generating an answer."

    # ── Step 4: Output guardrail ────────────────────────────────────────────
    print("\n[Step 4: Output Guardrail]")
    span = tracer.start_span("output_guard")
    output_result = output_check(answer, retrieved_chunks)
    span.finish(
        status="success",
        confidence=output_result.confidence,
        score=output_result.score,
        needs_review=output_result.needs_review,
    )

    # ── Step 5: HITL gate ───────────────────────────────────────────────────
    hitl_span    = tracer.start_span("hitl")
    final_answer = review(question, answer, output_result)

    if output_result.needs_review:
        hitl_span.finish(status="success", reviewed=True)
    else:
        hitl_span.finish(status="success", reviewed=False)

    # ── Finish trace ────────────────────────────────────────────────────────
    tracer.finish_run(
        status="success",
        final_answer=final_answer[:200],
    )

    print(f"\n[Final Answer]\n{final_answer}")
    return final_answer