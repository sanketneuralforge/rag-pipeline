# agents/retriever.py

import json
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
    Takes the original question and rewritten queries.
    Returns all retrieved chunks as a single formatted string.
    """
    print(f"  [Retriever] Executing {len(queries)} queries")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"User question: {question}\n\n"
                f"Search queries to execute: {json.dumps(queries)}"
            ),
        },
    ]

    all_results = []

    # Run the retrieval loop — same ReAct mechanics as the single agent
    # but this agent only ever calls retrieval tools, never synthesizes
    for _ in range(len(queries) + 2):   # enough iterations for all queries
        response = _call_llm(messages)

        if not response.tool_calls:
            # No more tool calls — retrieval complete
            break

        for tool_call in response.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            print(f"  [Retriever] {tool_name}({tool_args})")

            result = execute_tool(tool_name, tool_args)
            all_results.append(result)

            # Append tool call + result to message history
            messages.append({
                "role":       "assistant",
                "content":    None,
                "tool_calls": [{
                    "id":       tool_call.id,
                    "type":     "function",
                    "function": {
                        "name":      tool_name,
                        "arguments": tool_call.function.arguments,
                    }
                }]
            })
            messages.append({
                "role":         "tool",
                "tool_call_id": tool_call.id,
                "content":      result,
            })

    combined = "\n\n========\n\n".join(all_results)
    print(f"  [Retriever] Retrieved {len(all_results)} result(s)")
    return combined


def _call_llm(messages: list[dict]):
    if PROVIDER == "anthropic":
        return _call_anthropic(messages)

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        tools=TOOLS,
    )
    return response.choices[0].message


def _call_anthropic(messages: list[dict]):
    import anthropic as ac
    from agent import _convert_tools_for_anthropic, _AnthropicResponseWrapper
    anth     = ac.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = anth.messages.create(
        model=CHAT_MODEL,
        max_tokens=1024,
        system=messages[0]["content"],
        messages=messages[1:],
        tools=_convert_tools_for_anthropic(),
    )
    return _AnthropicResponseWrapper(response)