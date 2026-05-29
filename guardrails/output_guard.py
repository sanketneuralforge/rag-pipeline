# guardrails/output_guard.py

import re

# ---------------------------------------------------------------------------
# Confidence thresholds
# These were chosen based on the Stage 5 eval results.
# Tune these after running your full eval suite.
# ---------------------------------------------------------------------------
HIGH_CONFIDENCE_THRESHOLD  = 0.65   # avg chunk score above this = high confidence
LOW_CONFIDENCE_THRESHOLD   = 0.50   # avg chunk score below this = low confidence
ABSTENTION_SCORE_THRESHOLD = 0.55   # if score is borderline, check for abstention

# Phrases that indicate the agent is uncertain
UNCERTAINTY_MARKERS = [
    "could not find",
    "cannot find",
    "not available",
    "no information",
    "not in the",
    "unable to find",
    "not found",
    "i don't have",
    "i do not have",
]

# Phrases that indicate confident assertion — risky when retrieval was weak
CONFIDENT_ASSERTION_MARKERS = [
    "the policy is",
    "the procedure is",
    "you must",
    "you should",
    "employees are required",
    "it is required",
    "according to",
    "the document states",
]


class OutputGuardResult:
    def __init__(
        self,
        confidence: str,       # "high" | "medium" | "low"
        score: float,          # 0.0 - 1.0
        needs_review: bool,    # True = send to HITL gate
        reason: str,
        flags: list[str],
    ):
        self.confidence   = confidence
        self.score        = score
        self.needs_review = needs_review
        self.reason       = reason
        self.flags        = flags


def check(
    answer: str,
    retrieved_chunks: str,
) -> OutputGuardResult:
    """
    Scores the output for confidence and hallucination risk.

    Signals used:
    1. Average retrieval similarity score from the chunks
    2. Whether the answer makes confident assertions with weak retrieval
    3. Whether the answer correctly abstains on low-confidence retrieval
    """
    flags  = []
    answer_lower = answer.lower()

    # ── Signal 1: average retrieval score ──────────────────────────────────
    avg_score = _extract_avg_score(retrieved_chunks)

    # ── Signal 2: confident assertion with weak retrieval ──────────────────
    has_confident_assertion = any(
        marker in answer_lower for marker in CONFIDENT_ASSERTION_MARKERS
    )
    has_uncertainty_marker = any(
        marker in answer_lower for marker in UNCERTAINTY_MARKERS
    )

    if avg_score < LOW_CONFIDENCE_THRESHOLD and has_confident_assertion:
        flags.append(
            f"Confident assertion with low retrieval score ({avg_score:.2f}). "
            f"Hallucination risk."
        )

    # ── Signal 3: answer length vs retrieval quality ────────────────────────
    # A very long answer with weak retrieval is a hallucination signal.
    if avg_score < LOW_CONFIDENCE_THRESHOLD and len(answer) > 400:
        flags.append(
            f"Long answer ({len(answer)} chars) with weak retrieval ({avg_score:.2f})."
        )

    # ── Determine confidence level ──────────────────────────────────────────
    if has_uncertainty_marker:
        # Agent correctly abstained — always high confidence in the abstention
        confidence   = "high"
        needs_review = False
        reason       = "Agent correctly abstained"

    elif avg_score >= HIGH_CONFIDENCE_THRESHOLD and not flags:
        confidence   = "high"
        needs_review = False
        reason       = f"Strong retrieval (avg score {avg_score:.2f})"

    elif avg_score >= LOW_CONFIDENCE_THRESHOLD and not flags:
        confidence   = "medium"
        needs_review = False
        reason       = f"Acceptable retrieval (avg score {avg_score:.2f})"

    else:
        confidence   = "low"
        needs_review = True
        reason       = f"Weak retrieval (avg score {avg_score:.2f}) with flags: {flags}"

    result = OutputGuardResult(
        confidence=confidence,
        score=avg_score,
        needs_review=needs_review,
        reason=reason,
        flags=flags,
    )

    icon = "⚠️ " if needs_review else "✅"
    print(f"  [OutputGuard] {icon} confidence={confidence}, score={avg_score:.2f}, review={needs_review}")
    if flags:
        for flag in flags:
            print(f"  [OutputGuard]    flag: {flag}")

    return result


def _extract_avg_score(retrieved_chunks: str) -> float:
    """
    Parses the average relevance score from the formatted chunk string.
    Chunks are formatted as: '[1] Source: Title (relevance: 0.72)'
    Falls back to 0.5 if no scores found.
    """
    scores = re.findall(r"relevance:\s*([\d.]+)", retrieved_chunks)

    if not scores:
        return 0.5   # neutral fallback when no scores present

    return sum(float(s) for s in scores) / len(scores)