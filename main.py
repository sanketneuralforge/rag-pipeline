# main.py
from agents.orchestrator import run

def main():
    questions = [
        # Tests retrieve_documents
        "How many PTO days do employees get per year?",
        "What is the rollback procedure for a bad deployment?",
        "Can I deploy on a Friday?",
        "What happens if I exceed the API rate limit?",
        "What is the password policy?",

        # Tests list_documents — agent should call list_documents tool
        "What topics are covered in the internal documents?",

        # Tests get_document — agent may need full doc to answer
        "Summarize the entire on-call rotation guide.",

        # Unanswerable — should trigger abstention
        "What is our company's revenue?",
    ]

    for question in questions:
        answer = run(question)
        print(f"\nAnswer: {answer}")
        print("-" * 60)

if __name__ == "__main__":
    main()