# tools.py

import json
from vector_store import retrieve, build_index

# build the index when this module is first imported
build_index()

# ---------------------------------------------------------------------------
# Tool schema — this is what the LLM reads to understand what tools exist
# and how to call them. The description is the most important part: the LLM
# uses it to decide WHEN to call this tool.
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "retrieve_documents",
            "description": (
                "Search the internal document corpus and return the most relevant "
                "chunks for a given query. Use this tool whenever you need information "
                "to answer the user's question. You can call it multiple times with "
                "different queries if the first retrieval is insufficient."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "A specific, focused search query. Be precise — "
                            "a narrow query retrieves better chunks than a broad one."
                        ),
                    }
                },
                "required": ["query"],
            },
        },
    }
]


# ---------------------------------------------------------------------------
# Tool executor — maps tool name → actual Python function
# When the LLM returns a tool call, we look up the name here and run it.
# ---------------------------------------------------------------------------
def execute_tool(tool_name: str, tool_args: dict) -> str:
    if tool_name == "retrieve_documents":
        query   = tool_args["query"]
        results = retrieve(query)
        return format_results(results)

    return f"Unknown tool: {tool_name}"


def format_results(chunks: list[dict]) -> str:
    """
    Format retrieved chunks into a string the LLM can read in context.
    We include the source title and score so the LLM can cite sources
    and self-assess retrieval quality.
    """
    if not chunks:
        return "No relevant documents found."

    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[{i}] Source: {chunk['doc_title']} (relevance: {chunk['score']:.2f})\n"
            f"{chunk['text']}"
        )

    return "\n\n---\n\n".join(parts)