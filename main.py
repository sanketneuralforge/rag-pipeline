# main.py — entry point
# main.py

from vector_store import build_index
from agent import run_agent

def main():
    # Build the vector index once at startup
    build_index()

    # Test questions — designed to cover different scenarios
    questions = [
        "How many PTO days do employees get per year?",
        "What is the rollback procedure for a bad deployment?",
        "Can I deploy on a Friday?",
        "What happens if I exceed the API rate limit?",
        "What is the password policy?",
        "What is our company's revenue?",   # unanswerable — should trigger abstention
    ]

    for question in questions:
        answer = run_agent(question)
        print(f"\nAnswer: {answer}")
        print("-" * 60)

if __name__ == "__main__":
    main()