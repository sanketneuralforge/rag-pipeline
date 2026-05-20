# evals/runner.py

import time
from evals.dataset import TEST_CASES
from evals.judge import judge_answer, judge_abstention, judge_citation
from agents.orchestrator import run


def run_evals(verbose: bool = True) -> dict:
    """
    Runs all test cases through the orchestrator and scores them.
    Returns a summary dict with pass rates for each eval level.
    """
    results = []

    for i, case in enumerate(TEST_CASES):
        print(f"\n[{i+1}/{len(TEST_CASES)}] {case['id']}: {case['question']}")

        start      = time.time()
        agent_answer = run(case["question"])
        elapsed    = round(time.time() - start, 2)

        result = {
            "id":           case["id"],
            "question":     case["question"],
            "answerable":   case["answerable"],
            "agent_answer": agent_answer,
            "latency_s":    elapsed,
        }

        # -----------------------------------------------------------------
        # Level 1 — Citation eval (did it cite the right source?)
        # -----------------------------------------------------------------
        citation = judge_citation(agent_answer, case["expected_sources"])
        result["citation_score"]  = citation["score"]
        result["citation_reason"] = citation["reason"]

        # -----------------------------------------------------------------
        # Level 2 — Answer eval (is the answer correct?)
        # Only runs on answerable questions with a reference answer.
        # -----------------------------------------------------------------
        if case["answerable"] and case["reference_answer"]:
            answer = judge_answer(
                case["question"],
                case["reference_answer"],
                agent_answer,
            )
            result["answer_score"]  = answer["score"]
            result["answer_reason"] = answer["reason"]
        else:
            result["answer_score"]  = None
            result["answer_reason"] = "Skipped — unanswerable question"

        # -----------------------------------------------------------------
        # Level 3 — Abstention eval (did it correctly say I don't know?)
        # Only runs on unanswerable questions.
        # -----------------------------------------------------------------
        if not case["answerable"]:
            abstention = judge_abstention(agent_answer)
            result["abstention_score"]  = abstention["score"]
            result["abstention_reason"] = abstention["reason"]
        else:
            result["abstention_score"]  = None
            result["abstention_reason"] = "Skipped — answerable question"

        results.append(result)

        if verbose:
            _print_case_result(result)

    return _print_summary(results)


def _print_case_result(result: dict) -> None:
    print(f"  Latency:   {result['latency_s']}s")
    print(f"  Answer:    {result['agent_answer'][:120]}")

    if result["answer_score"] is not None:
        icon = "✅" if result["answer_score"] == 1 else "❌"
        print(f"  L2 Answer: {icon} {result['answer_reason']}")

    if result["abstention_score"] is not None:
        icon = "✅"