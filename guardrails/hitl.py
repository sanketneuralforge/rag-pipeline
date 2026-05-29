# guardrails/hitl.py

from guardrails.output_guard import OutputGuardResult


def review(
    question: str,
    answer: str,
    guard_result: OutputGuardResult,
) -> str:
    """
    Presents a low-confidence answer to a human for approval.

    Returns:
      - The original answer if approved
      - A safe fallback message if rejected
      - The original answer untouched if review is not needed
    """
    if not guard_result.needs_review:
        return answer

    _print_review_panel(question, answer, guard_result)

    decision = _get_decision()

    if decision == "a":
        print("  [HITL] Answer approved. Returning to user.")
        return answer

    if decision == "e":
        edited = _get_edited_answer()
        print("  [HITL] Edited answer accepted.")
        return edited

    # Rejected
    print("  [HITL] Answer rejected. Returning safe fallback.")
    return (
        "I was not confident enough in my answer to share it. "
        "Please rephrase your question or consult the source documents directly."
    )


def _print_review_panel(
    question: str,
    answer: str,
    guard_result: OutputGuardResult,
) -> None:
    print("\n" + "=" * 60)
    print("⚠️  HUMAN REVIEW REQUIRED")
    print("=" * 60)
    print(f"Question:   {question}")
    print(f"Confidence: {guard_result.confidence.upper()} (score: {guard_result.score:.2f})")
    print(f"Reason:     {guard_result.reason}")

    if guard_result.flags:
        print("Flags:")
        for flag in guard_result.flags:
            print(f"  • {flag}")

    print(f"\nProposed answer:\n{answer}")
    print("=" * 60)


def _get_decision() -> str:
    """
    Prompts the human for a decision.
    Returns 'a' (approve), 'r' (reject), or 'e' (edit).
    Loops until a valid choice is made.
    """
    while True:
        choice = input(
            "\n[HITL] Decision — (a) approve  (r) reject  (e) edit: "
        ).strip().lower()

        if choice in ("a", "r", "e"):
            return choice

        print("  Invalid choice. Enter a, r, or e.")


def _get_edited_answer() -> str:
    """Prompts the human to type a replacement answer."""
    print("\n[HITL] Type your replacement answer. Press Enter twice when done.")
    lines = []
    while True:
        line = input()
        if line == "" and lines:
            break
        lines.append(line)
    return "\n".join(lines)