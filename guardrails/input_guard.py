# guardrails/input_guard.py

import re

# ---------------------------------------------------------------------------
# Prompt injection patterns
# These are phrases that signal an attempt to hijack the agent's behavior.
# Rules-based: fast, zero latency, zero cost, catches 80% of real attacks.
# ---------------------------------------------------------------------------
INJECTION_PATTERNS = [
    r"ignore (previous|prior|all|your) instructions",
    r"forget (previous|prior|all|your) instructions",
    r"your new instructions",
    r"pretend (you are|to be|you're)",
    r"act as (if you are|a|an)",
    r"you are now",
    r"disregard (previous|prior|all)",
    r"override (previous|prior|your)",
    r"do not follow",
    r"bypass (your|the) (instructions|rules|guidelines)",
    r"reveal (your|the) (system prompt|instructions|prompt)",
    r"print (your|the) (system prompt|instructions)",
    r"what are your instructions",
    r"jailbreak",
    r"dan mode",
]

# ---------------------------------------------------------------------------
# Off-topic signals
# Questions clearly outside what a company knowledge base can answer.
# We flag these rather than hard-blocking — the agent can still attempt
# to answer and abstain gracefully if nothing is found.
# ---------------------------------------------------------------------------
OFF_TOPIC_PATTERNS = [
    r"\b(stock price|share price|market cap)\b",
    r"\b(weather|forecast|temperature)\b",
    r"\b(recipe|cook|bake|ingredient)\b",
    r"\b(sports|score|match|game)\b",
    r"\b(celebrity|actor|actress|singer)\b",
    r"\b(news|headline|breaking)\b",
]


class InputGuardResult:
    def __init__(self, allowed: bool, reason: str, warning: str = None):
        self.allowed = allowed    # False = hard block, True = allow through
        self.reason  = reason     # shown in logs
        self.warning = warning    # shown to orchestrator if flagged but allowed


def check(user_input: str) -> InputGuardResult:
    """
    Runs all input checks. Returns a result indicating whether the input
    should be allowed, blocked, or allowed with a warning.
    """
    text = user_input.lower().strip()

    # Hard block: prompt injection
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text):
            print(f"  [InputGuard] BLOCKED — injection pattern matched: '{pattern}'")
            return InputGuardResult(
                allowed=False,
                reason=f"Prompt injection detected: '{pattern}'",
            )

    # Soft flag: off-topic
    for pattern in OFF_TOPIC_PATTERNS:
        if re.search(pattern, text):
            print(f"  [InputGuard] WARNING — off-topic pattern: '{pattern}'")
            return InputGuardResult(
                allowed=True,
                reason="Off-topic signal detected",
                warning="This question may be outside the scope of internal documents.",
            )

    # Empty input
    if len(text) < 3:
        return InputGuardResult(
            allowed=False,
            reason="Input too short to be a valid question",
        )

    print(f"  [InputGuard] PASSED")
    return InputGuardResult(allowed=True, reason="Clean input")