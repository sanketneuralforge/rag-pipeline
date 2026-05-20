# agents/query_rewriter.py

import json
from openai import OpenAI
from config import (
    PROVIDER,
    OLLAMA_BASE_URL, OLLAMA_CHAT_MODEL,
    OPENAI_API_KEY, OPENAI_CHAT_MODEL,
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
)

# ---------------------------------------------------------------------------
# Provider setup — same pattern as agent.py
# ---------------------------------------------------------------------------
if PROVIDER == "ollama":
    client     = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    CHAT_MODEL = OLLAMA_CHAT_MODEL
elif PROVIDER == "openai":
    client     = OpenAI(api_key=OPENAI_API_KEY)
    CHAT_MODEL = OPENAI_CHAT_MODEL
else:
    client     = None
    CHAT_MODEL = ANTHROPIC_MODEL

SYSTEM_PROMPT = """You are a search query optimization expert. Your only job is 
to rewrite a user's question into 2-3 short, focused search queries that will 
retrieve the most relevant document chunks from a company knowledge base.

Rules:
1. Return ONLY a JSON array of query strings. No explanation, no preamble.
2. Each query must be short and specific — 3 to 7 words maximum.
3. Use different vocabulary in each query to maximize retrieval coverage.
4. Never use markdown formatting like ** in your queries.
5. Think about synonyms — what words might the document use vs what the user said?
6. Avoid ambiguous single words that could match unrelated topics.
7. Always include one query that preserves the key literal terms from the question.

Example input: "What happens if I don't come to work for a week?"
Example output: ["unplanned absence employee policy", "sick leave days per year", "employee attendance expectations"]
"""


def rewrite(question: str) -> list[str]:
    """
    Takes the user's raw question.
    Returns a list of 2-3 optimized search query strings.
    """
    print(f"  [QueryRewriter] Rewriting: '{question}'")

    messages = [
        {"role": "system",  "content": SYSTEM_PROMPT},
        {"role": "user",    "content": question},
    ]

    response = _call_llm(messages)
    queries  = _parse_queries(response, question)

    print(f"  [QueryRewriter] Generated queries: {queries}")
    return queries


def _call_llm(messages: list[dict]) -> str:
    if PROVIDER == "anthropic":
        import anthropic as ac
        anth     = ac.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = anth.messages.create(
            model=CHAT_MODEL,
            max_tokens=256,
            system=messages[0]["content"],
            messages=messages[1:],
        )
        return response.content[0].text

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        max_tokens=256,
    )
    return response.choices[0].message.content


def _parse_queries(response: str, fallback_question: str) -> list[str]:
    """
    Parse the JSON array from the LLM response.
    Falls back to the original question if parsing fails.

    Production gotcha: always have a fallback when parsing LLM output.
    Even with explicit instructions, models occasionally return malformed JSON.
    """
    try:
        # Strip any accidental markdown code fences
        clean = response.strip().strip("```json").strip("```").strip()
        queries = json.loads(clean)

        if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
            return queries[:3]  # cap at 3 queries

    except (json.JSONDecodeError, ValueError):
        print(f"  [QueryRewriter] Failed to parse response, using original question")

    return [fallback_question]