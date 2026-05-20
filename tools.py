# tools.py

import json
from vector_store import build_index, retrieve, list_documents, get_document

# Build index on import — skips automatically if already built
build_index()


# ---------------------------------------------------------------------------
# Tool schemas — what the LLM reads to decide which tool to call and when
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "retrieve_documents",
            "description": (
                "Search the internal document corpus and return the most relevant "
                "chunks for a given query. Use this as your first action for any "
                "question. Call it multiple times with different queries if the "
                "first retrieval is insufficient."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "A specific, focused search query. Narrow queries "
                            "retrieve better chunks than broad ones."
                        ),
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_documents",
            "description": (
                "List all documents available in the corpus with their IDs and titles. "
                "Use this when you want to know what documents exist before searching, "
                "or when the user asks what topics are covered."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_document",
            "description": (
                "Retrieve the full content of a specific document by its ID. "
                "Use this when retrieved chunks are insufficient and you need "
                "to read the complete document. Get the document ID from "
                "list_documents first."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": "The document ID, e.g. 'hr-pto-001'",
                    }
                },
                "required": ["doc_id"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool executor — maps tool name → Python function
# ---------------------------------------------------------------------------
def execute_tool(tool_name: str, tool_args: dict) -> str:
    if tool_name == "retrieve_documents":
        query = tool_args["query"]
        # Guard: Mistral sometimes passes a list instead of a string
        if isinstance(query, list):
            query = " ".join(query)
        results = retrieve(query)
        return _format_chunks(results)

    if tool_name == "list_documents":
        docs = list_documents()
        return _format_document_list(docs)

    if tool_name == "get_document":
        doc = get_document(tool_args["doc_id"])
        if doc is None:
            return f"Document '{tool_args['doc_id']}' not found in corpus."
        return f"Document: {doc['title']}\n\n{doc['content']}"

    return f"Unknown tool: {tool_name}"


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------
def _format_chunks(chunks: list[dict]) -> str:
    if not chunks:
        return "No relevant documents found."

    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[{i}] Source: {chunk['doc_title']} "
            f"(relevance: {chunk['score']:.2f})\n"
            f"{chunk['text']}"
        )

    return "\n\n---\n\n".join(parts)


def _format_document_list(docs: list[dict]) -> str:
    if not docs:
        return "No documents found in corpus."

    lines = ["Available documents:\n"]
    for doc in docs:
        lines.append(f"  - {doc['id']}: {doc['title']}")

    return "\n".join(lines)