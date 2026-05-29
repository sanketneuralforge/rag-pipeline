# main.py

import sys
from agents.orchestrator import run
from evals.runner import run_evals
from observability.dashboard import print_dashboard


def main():
    if "--eval" in sys.argv:
        run_evals()
        print_dashboard()
        return

    if "--dashboard" in sys.argv:
        print_dashboard()
        return

    questions = [
        "How many PTO days do employees get per year?",
        "What is the rollback procedure for a bad deployment?",
        # "Can I deploy on a Friday?",
        # "What happens if I exceed the API rate limit?",
        # "What is our company's revenue?",
    ]

    for question in questions:
        answer = run(question)
        print(f"\nAnswer: {answer}")
        print("-" * 60)

    print_dashboard(last_n=len(questions))


if __name__ == "__main__":
    main()