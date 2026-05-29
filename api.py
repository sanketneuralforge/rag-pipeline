# api.py

import time
import os
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from agents.orchestrator import run
from observability.metrics import load_traces, compute_metrics
from observability.tracer import TRACES_DIR

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Research Assistant Agent",
    description="A RAG agent that answers questions from internal documents.",
    version="1.0.0",
)

# CORS — allows browser clients to call the API directly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# Pydantic validates incoming JSON automatically — bad requests return 422
# ---------------------------------------------------------------------------
class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The question to ask the agent",
        example="How many PTO days do employees get per year?",
    )


class SpanResponse(BaseModel):
    name:       str
    duration_s: float
    status:     str
    metadata:   dict


class AskResponse(BaseModel):
    run_id:     str
    question:   str
    answer:     str
    confidence: str         # "high" | "medium" | "low"
    latency_s:  float
    spans:      list[SpanResponse]


class HealthResponse(BaseModel):
    status:     str
    version:    str
    index_ready: bool


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse, tags=["System"])
def health():
    """
    Liveness check. Load balancers call this to verify the service is up.
    Returns index_ready so you know if the vector store is built.
    """
    from vector_store import _store
    return HealthResponse(
        status="ok",
        version="1.0.0",
        index_ready=_store.collection.count() > 0,
    )


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
def ask(request: AskRequest):
    """
    Main endpoint. Runs the full agent pipeline and returns a structured response.

    The response includes:
    - answer: the synthesized answer with citations
    - confidence: high / medium / low based on retrieval quality
    - latency_s: total time taken
    - spans: per-step timing breakdown for debugging
    """
    start = time.time()

    try:
        answer = run(request.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    # Load the trace that was just written
    traces = load_traces(last_n=1)
    trace  = traces[0] if traces else {}

    # Extract confidence from output_guard span
    confidence = "medium"
    spans      = []
    for span in trace.get("spans", []):
        spans.append(SpanResponse(
            name       = span["name"],
            duration_s = span.get("duration_s", 0),
            status     = span.get("status", "unknown"),
            metadata   = span.get("metadata", {}),
        ))
        if span["name"] == "output_guard":
            confidence = span.get("metadata", {}).get("confidence", "medium")

    return AskResponse(
        run_id     = trace.get("run_id", "unknown"),
        question   = request.question,
        answer     = answer,
        confidence = confidence,
        latency_s  = round(time.time() - start, 3),
        spans      = spans,
    )


@app.get("/metrics", tags=["Observability"])
def metrics():
    """
    Returns aggregate metrics across recent runs as JSON.
    Same data as the terminal dashboard but machine-readable.
    """
    traces  = load_traces(last_n=50)
    metrics = compute_metrics(traces)

    if not metrics:
        return {"message": "No runs recorded yet"}

    return metrics


@app.get("/traces/{run_id}", tags=["Observability"])
def get_trace(run_id: str):
    """
    Returns the full trace for a specific run by ID.
    Use this to debug a specific failed run in production.
    """
    path = os.path.join(TRACES_DIR, f"{run_id}.json")

    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail=f"Trace {run_id} not found"
        )

    with open(path) as f:
        return json.load(f)


@app.get("/traces", tags=["Observability"])
def list_traces(limit: int = 10):
    """
    Lists recent run IDs and their status.
    """
    traces = load_traces(last_n=limit)

    return [
        {
            "run_id":     t.get("run_id"),
            "status":     t.get("status"),
            "duration_s": t.get("duration_s"),
            "question":   t.get("question", "")[:80],
        }
        for t in traces
    ]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)