# main.py

import sys
from agents.orchestrator import run
from evals.runner import run_evals


def main():
    # Run evals if --eval flag passed
    if "--eval" in sys.argv:
        run_evals()
        return

    questions = [
        "How many PTO days do employees get per year?",
        "What is the rollback procedure for a bad deployment?",
        "Can I deploy on a Friday?",
        "What happens if I exceed the API rate limit?",
        "What is the password policy?",
        "What topics are covered in the internal documents?",
        "Summarize the entire on-call rotation guide.",
        "What is our company's revenue?",
    ]

    for question in questions:
        answer = run(question)
        print(f"\nAnswer: {answer}")
        print("-" * 60)


if __name__ == "__main__":
    main()