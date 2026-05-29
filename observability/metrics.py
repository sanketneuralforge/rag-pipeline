# observability/metrics.py

import json
import os
from observability.tracer import TRACES_DIR


def load_traces(last_n: int = None) -> list[dict]:
    """
    Loads trace files from disk, sorted by start time (newest first).
    Optionally limits to the last N runs.
    """
    if not os.path.exists(TRACES_DIR):
        return []

    files = [
        f for f in os.listdir(TRACES_DIR)
        if f.endswith(".json")
    ]

    traces = []
    for filename in files:
        path = os.path.join(TRACES_DIR, filename)
        try:
            with open(path) as f:
                traces.append(json.load(f))
        except (json.JSONDecodeError, IOError):
            continue

    # Sort newest first
    traces.sort(key=lambda t: t.get("start_time", 0), reverse=True)

    if last_n:
        return traces[:last_n]
    return traces


# ── Helpers defined BEFORE compute_metrics ──────────────────────────────────

def _answer_abstained(answer: str) -> bool:
    ABSTENTION_MARKERS = [
        "could not find", "cannot find", "not available",
        "no information", "not in the", "unable to find",
    ]
    answer_lower = answer.lower()
    return any(m in answer_lower for m in ABSTENTION_MARKERS)


def _had_hitl_review(trace: dict) -> bool:
    for span in trace.get("spans", []):
        if span.get("name") == "hitl":
            # Only count as HITL if actually reviewed
            return span.get("metadata", {}).get("reviewed", False)
    return False


def _percentile(sorted_values: list, pct: int) -> float:
    if not sorted_values:
        return 0.0
    index = min(int(len(sorted_values) * pct / 100), len(sorted_values) - 1)
    return round(sorted_values[index], 3)


def _compute_span_latencies(traces: list[dict]) -> dict:
    """Average latency per span type across all runs."""
    span_times  = {}
    span_counts = {}

    for trace in traces:
        for span in trace.get("spans", []):
            name = span["name"]
            dur  = span.get("duration_s", 0)
            span_times[name]  = span_times.get(name, 0) + dur
            span_counts[name] = span_counts.get(name, 0) + 1

    return {
        name: round(span_times[name] / span_counts[name], 3)
        for name in span_times
    }


# ── Main function ────────────────────────────────────────────────────────────

def compute_metrics(traces: list[dict]) -> dict:
    """
    Computes aggregate metrics across a list of traces.

    Production metrics every RAG system should track:
    - Task completion rate: did the agent produce an answer?
    - Abstention rate: how often did it say 'I don't know'?
    - Error rate: how often did a span fail?
    - Latency p50/p90: median and 90th percentile response time
    - Avg retrieval relevance: how good is retrieval quality?
    - HITL rate: how often did we need human review?
    """
    if not traces:
        return {}

    total = len(traces)

    # --- Completion rate ---
    completed   = sum(1 for t in traces if t.get("status") == "success")
    error_count = sum(1 for t in traces if t.get("status") == "error")

    # --- Abstention rate ---
    abstentions = sum(
        1 for t in traces
        if _answer_abstained(
            t.get("metadata", {}).get("final_answer", "")
        )
    )

    # --- Latency ---
    # duration_s can be at top level or computed from start/end time
    durations = []
    for t in traces:
        if "duration_s" in t and t["duration_s"] is not None:
            durations.append(t["duration_s"])
        elif "start_time" in t and "end_time" in t and t["end_time"]:
            durations.append(round(t["end_time"] - t["start_time"], 3))

    durations.sort()
    p50 = _percentile(durations, 50) if durations else 0.0
    p90 = _percentile(durations, 90) if durations else 0.0

    # --- Retrieval relevance ---
    relevances = [
        t["avg_relevance"]
        for t in traces
        if t.get("avg_relevance") is not None
    ]
    avg_relevance = (
        round(sum(relevances) / len(relevances), 3)
        if relevances else None
    )

    # --- HITL rate ---
    hitl_count = sum(1 for t in traces if _had_hitl_review(t))

    # --- Per-span latency breakdown ---
    span_latencies = _compute_span_latencies(traces)

    return {
        "total_runs":      total,
        "completion_rate": round(completed / total, 3),
        "error_rate":      round(error_count / total, 3),
        "abstention_rate": round(abstentions / total, 3),
        "latency_p50_s":   p50,
        "latency_p90_s":   p90,
        "avg_relevance":   avg_relevance,
        "hitl_rate":       round(hitl_count / total, 3),
        "span_latencies":  span_latencies,
    }