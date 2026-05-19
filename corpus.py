# corpus.py

import os

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")

# Maps filename stem → human readable title
TITLE_MAP = {
    "hr-pto-001":          "PTO & Leave Policy",
    "eng-deploy-001":      "Production Deployment Runbook",
    "eng-oncall-001":      "On-Call Rotation Guide",
    "product-api-001":     "Public API Rate Limits",
    "product-pricing-001": "Pricing & Plans",
    "security-001":        "Security & Compliance",
}


def load_documents() -> list[dict]:
    """
    Load all .txt files from the docs/ directory.
    Returns the same shape as before — list of dicts with id, title, content —
    so nothing downstream needs to change.
    """
    documents = []

    for filename in sorted(os.listdir(DOCS_DIR)):
        if not filename.endswith(".txt"):
            continue

        doc_id    = filename.replace(".txt", "")
        title     = TITLE_MAP.get(doc_id, doc_id)
        filepath  = os.path.join(DOCS_DIR, filename)

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()

        documents.append({
            "id":      doc_id,
            "title":   title,
            "content": content,
        })

    print(f"Loaded {len(documents)} documents from {DOCS_DIR}")
    return documents


# Module-level constant — same interface as before
DOCUMENTS = load_documents()