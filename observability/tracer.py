# observability/tracer.py

import json
import time
import uuid
import os
from dataclasses import dataclass, field, asdict
from typing import Optional

TRACES_DIR = os.path.join(os.path.dirname(__file__), "..", "traces")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class Span:
    """
    One step in the agent pipeline.
    Captures name, timing, status, and any metadata relevant to that step.
    """
    name:       str
    start_time: float = field(default_factory=time.time)
    end_time:   float = None
    status:     str   = "running"   # "running" | "success" | "error"
    metadata:   dict  = field(default_factory=dict)
    error:      str   = None

    def finish(self, status: str = "success", **metadata):
        self.end_time = time.time()
        self.status   = status
        self.metadata.update(metadata)

    def fail(self, error: str):
        self.end_time = time.time()
        self.status   = "error"
        self.error    = error

    @property
    def duration_s(self) -> float:
        if self.end_time:
            return round(self.end_time - self.start_time, 3)
        return round(time.time() - self.start_time, 3)


@dataclass
class Trace:
    """
    One complete agent run — contains all spans for that run.
    """
    run_id:     str   = field(default_factory=lambda: str(uuid.uuid4())[:8])
    question:   str   = ""
    start_time: float = field(default_factory=time.time)
    end_time:   float = None
    status:     str   = "running"
    spans:      list  = field(default_factory=list)
    metadata:   dict  = field(default_factory=dict)

    def start_span(self, name: str) -> Span:
        span = Span(name=name)
        self.spans.append(span)
        return span

    def finish(self, status: str = "success", **metadata):
        self.end_time = time.time()
        self.status   = status
        self.metadata.update(metadata)

    @property
    def duration_s(self) -> float:
        if self.end_time:
            return round(self.end_time - self.start_time, 3)
        return round(time.time() - self.start_time, 3)

    @property
    def total_tokens(self) -> int:
        """Sum token counts across all spans that reported them."""
        return sum(
            s.metadata.get("tokens", 0)
            for s in self.spans
        )

    @property
    def avg_relevance(self) -> Optional[float]:
        """Average retrieval relevance score across all spans."""
        scores = [
            s.metadata["avg_relevance"]
            for s in self.spans
            if "avg_relevance" in s.metadata
        ]
        if not scores:
            return None
        return round(sum(scores) / len(scores), 3)


# ---------------------------------------------------------------------------
# Tracer — manages the active trace for a single run
# ---------------------------------------------------------------------------
class Tracer:
    def __init__(self):
        self._trace: Optional[Trace] = None

    def start_run(self, question: str) -> Trace:
        self._trace = Trace(question=question)
        print(f"  [Tracer] Run {self._trace.run_id} started")
        return self._trace

    def start_span(self, name: str) -> Span:
        if not self._trace:
            raise RuntimeError("Call start_run() before start_span()")
        return self._trace.start_span(name)

    def finish_run(self, status: str = "success", **metadata) -> Trace:
        if not self._trace:
            raise RuntimeError("No active run")
        self._trace.finish(status=status, **metadata)
        self._persist()
        print(f"  [Tracer] Run {self._trace.run_id} finished — "
              f"{status} in {self._trace.duration_s}s")
        return self._trace

    def _persist(self):
        """Write trace to disk as JSON. One file per run."""
        os.makedirs(TRACES_DIR, exist_ok=True)
        path = os.path.join(
            TRACES_DIR,
            f"{self._trace.run_id}.json"
        )
        with open(path, "w") as f:
            json.dump(self._to_dict(), f, indent=2)

    def _to_dict(self) -> dict:
        t = self._trace
        return {
            "run_id":      t.run_id,
            "question":    t.question,
            "start_time":  t.start_time,
            "end_time":    t.end_time,
            "duration_s":  t.duration_s,
            "status":      t.status,
            "metadata":    t.metadata,
            "total_tokens": t.total_tokens,
            "avg_relevance": t.avg_relevance,
            "spans": [
                {
                    "name":       s.name,
                    "duration_s": s.duration_s,
                    "status":     s.status,
                    "metadata":   s.metadata,
                    "error":      s.error,
                }
                for s in t.spans
            ]
        }


# ---------------------------------------------------------------------------
# Module-level singleton — one tracer per process
# ---------------------------------------------------------------------------
tracer = Tracer()