# agents/retriever.py

import json
import asyncio
from openai import OpenAI
from config import (
    PROVIDER,
    OLLAMA_BASE_URL, OLLAMA_CHAT_MODEL,
    OPENAI_API_KEY, OPENAI_CHAT_MODEL,
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
)
from tools import TOOLS, execute_tool

if PROVIDER == "ollama":
    client     = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    CHAT_MODEL = OLLAMA_CHAT_MODEL
elif PROVIDER == "openai":
    client     = OpenAI(api_key=OPENAI_API_KEY)
    CHAT_MODEL = OPENAI_CHAT_MODEL
else:
    client     = None
    CHAT_MODEL = ANTHROPIC_MODEL

SYSTEM_PROMPT = """You are a document retrieval specialist. You are given a user 
question and a list of search queries. Your job is to retrieve the most relevant 
information from the knowledge base using the available tools.

Rules:
1. For each query provided, call retrieve_documents with that exact query.
2. If the question asks to summarize or explain an entire document, call 
   list_documents first to find the document ID, then call get_document.
3. Do not synthesize or answer — only retrieve. Return all retrieved content.
4. Stop after you have retrieved content for all queries.
"""


def retrieve(question: str, queries: list[str]) -> str:
    """
    Public interface — runs async retrieval and returns combined results.
    Wraps the async function so callers don't need to manage event loops.
    """
    return asyncio.run(_retrieve_async(question, queries))


async def _retrieve_async(question: str, queries: list[str]) -> str:
    """
    Executes all queries in parallel using asyncio.gather.

    Key concept: asyncio.gather() runs all coroutines concurrently.
    Instead of: query1(3s) → query2(3s) → query3(3s) = 9s total
    We get:     query1, query2, query3 all at once = ~3s total

    Production gotcha: asyncio parallelism helps with I/O-bound work
    (API calls, network requests). It does NOT help with CPU-bound work.
    Embedding and LLM calls are I/O-bound — perfect fit for asyncio.
    """
    print(f"  [Retriever] Executing {len(queries)} queries in parallel")

    # Create one coroutine per query and run them all concurrently
    tasks   = [_execute_single_query(query) for query in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out exceptions — a single failed query should not crash everything
    all_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"  [Retriever] Query {i+1} failed: {result}")
        else:
            all_results.append(result)

    print(f"  [Retriever] Retrieved {len(all_results)} result(s)")
    return "\n\n========\n\n".join(all_results)


async def _execute_single_query(query: str) -> str:
    """
    Executes a single query against the vector store.
    Runs in a thread pool to avoid blocking the event loop —
    the OpenAI client is synchronous, so we use run_in_executor
    to make it non-blocking.
    """
    loop = asyncio.get_event_loop()

    # run_in_executor moves the blocking call to a thread pool
    # This is the correct pattern for using sync libraries in async code
    result = await loop.run_in_executor(
        None,   # None = default thread pool executor
        lambda: _sync_retrieve(query)
    )
    return result


def _sync_retrieve(query: str) -> str:
    """
    Synchronous single-query retrieval.
    Called from the thread pool via run_in_executor.
    """
    print(f"  [Retriever] retrieve_documents({{'query': '{query}'}})")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Execute this search query: {query}",
        },
    ]

    # Simple single-tool call — no loop needed for individual queries
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        tools=TOOLS,
        max_tokens=512,
    )

    msg = response.choices[0].message

    if msg.tool_calls:
        tool_call = msg.tool_calls[0]
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)

        # Coerce list to string — Mistral sometimes wraps query in a list
        if isinstance(tool_args.get("query"), list):
            tool_args["query"] = " ".join(tool_args["query"])

        return execute_tool(tool_name, tool_args)

    # Model returned text instead of tool call — return it as-is
    return msg.content or ""