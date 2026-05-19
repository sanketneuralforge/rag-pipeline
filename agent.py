# agent.py

import json
from openai import OpenAI
from config import (
    PROVIDER,
    OLLAMA_BASE_URL, OLLAMA_CHAT_MODEL,
    OPENAI_API_KEY, OPENAI_CHAT_MODEL,
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
    MAX_ITERATIONS,
)
from tools import TOOLS, execute_tool

# ---------------------------------------------------------------------------
# Provider setup for chat
# ---------------------------------------------------------------------------
if PROVIDER == "ollama":
    client     = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    CHAT_MODEL = OLLAMA_CHAT_MODEL
elif PROVIDER == "openai":
    client     = OpenAI(api_key=OPENAI_API_KEY)
    CHAT_MODEL = OPENAI_CHAT_MODEL
else:
    # Anthropic — we use the openai-compatible shim for now.
    # In Stage 4 we'll switch to the native Anthropic client.
    import anthropic
    client     = None   # handled separately below
    CHAT_MODEL = ANTHROPIC_MODEL


SYSTEM_PROMPT = """You are a helpful internal knowledge assistant. You answer 
questions strictly based on the company's internal documents.

Rules you must follow:
1. You MUST call retrieve_documents as your very first action. No exceptions.
2. Never answer from memory. Always retrieve first.
3. Base your answer ONLY on retrieved document content.
4. Always cite the source document title for every claim you make.
5. If the retrieved documents do not contain enough information to answer the 
   question, say exactly: "I could not find an answer in the available documents."
6. If your first retrieval is insufficient, try again with a different query.
"""


# ---------------------------------------------------------------------------
# Core ReAct loop
# ---------------------------------------------------------------------------
def run_agent(user_question: str) -> str:
    print(f"\n{'='*60}")
    print(f"Question: {user_question}")
    print(f"{'='*60}")

    messages = [
        {"role": "system",  "content": SYSTEM_PROMPT},
        {"role": "user",    "content": user_question},
    ]

    for iteration in range(MAX_ITERATIONS):
        print(f"\n[Iteration {iteration + 1}]")

        # --- Think: call the LLM ---
        response = _call_llm(messages)

        # --- Check: did the LLM call a tool or produce a final answer? ---
        if response.tool_calls:
            # LLM wants to use a tool
            for tool_call in response.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                print(f"  Tool call: {tool_name}({tool_args})")

                # --- Act: run the tool ---
                tool_result = execute_tool(tool_name, tool_args)

                print(f"  Result preview: {tool_result[:120]}...")

                # Append assistant's tool call to message history
                messages.append({
                    "role":       "assistant",
                    "content":    None,
                    "tool_calls": [
                        {
                            "id":       tool_call.id,
                            "type":     "function",
                            "function": {
                                "name":      tool_name,
                                "arguments": tool_call.function.arguments,
                            }
                        }
                    ]
                })

                # Append tool result to message history
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tool_call.id,
                    "content":      tool_result,
                })

        else:
            # No tool call — this is the final answer
            final_answer = response.content
            print(f"\n[Final Answer]\n{final_answer}")
            return final_answer

    # If we exit the loop without a final answer, force a synthesis
    print("\n[Max iterations reached — forcing final answer]")
    messages.append({
        "role":    "user",
        "content": "Based on everything retrieved so far, give your final answer now."
    })
    response  = _call_llm(messages, tools=False)
    return response.content


# ---------------------------------------------------------------------------
# LLM call — abstracted so the ReAct loop doesn't care about provider details
# ---------------------------------------------------------------------------
def _call_llm(messages: list[dict], tools: bool = True):
    if PROVIDER == "anthropic":
        return _call_anthropic(messages, tools)

    kwargs = {
        "model":    CHAT_MODEL,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = TOOLS

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message


def _call_anthropic(messages: list[dict], tools: bool = True):
    """
    Native Anthropic client call.
    Wraps the response to match the openai-style interface the loop expects.
    """
    import anthropic as ac

    anth   = ac.Anthropic(api_key=ANTHROPIC_API_KEY)
    kwargs = {
        "model":      CHAT_MODEL,
        "max_tokens": 1024,
        "system":     messages[0]["content"],
        "messages":   messages[1:],
    }
    if tools:
        kwargs["tools"] = _convert_tools_for_anthropic()

    response = anth.messages.create(**kwargs)

    # Wrap into an openai-style object so the ReAct loop works unchanged
    return _AnthropicResponseWrapper(response)


def _convert_tools_for_anthropic() -> list[dict]:
    """Anthropic uses a slightly different tool schema format."""
    converted = []
    for tool in TOOLS:
        converted.append({
            "name":         tool["function"]["name"],
            "description":  tool["function"]["description"],
            "input_schema": tool["function"]["parameters"],
        })
    return converted


class _AnthropicResponseWrapper:
    """
    Thin wrapper so Anthropic responses look like OpenAI responses to the loop.
    This is the adapter pattern — insulate your core logic from provider quirks.
    """
    def __init__(self, response):
        self._response  = response
        self.tool_calls = self._extract_tool_calls()
        self.content    = self._extract_text()

    def _extract_tool_calls(self):
        calls = []
        for block in self._response.content:
            if block.type == "tool_use":
                calls.append(_AnthropicToolCallWrapper(block))
        return calls if calls else None

    def _extract_text(self):
        for block in self._response.content:
            if block.type == "text":
                return block.text
        return ""


class _AnthropicToolCallWrapper:
    """Makes an Anthropic tool_use block look like an OpenAI tool_call."""
    def __init__(self, block):
        self.id       = block.id
        self.function = _AnthropicFunctionWrapper(block)


class _AnthropicFunctionWrapper:
    def __init__(self, block):
        self.name      = block.name
        self.arguments = json.dumps(block.input)