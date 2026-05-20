# agents/synthesizer.py

from openai import OpenAI
from config import (
    PROVIDER,
    OLLAMA_BASE_URL, OLLAMA_CHAT_MODEL,
    OPENAI_API_KEY, OPENAI_CHAT_MODEL,
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
)

if PROVIDER == "ollama":
    client     = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    CHAT_MODEL = OLLAMA_CHAT_MODEL
elif PROVIDER == "openai":
    client     = OpenAI(api_key=OPENAI_API_KEY)
    CHAT_MODEL = OPENAI_CHAT_MODEL
else:
    client     = None
    CHAT_MODEL = ANTHROPIC_MODEL

SYSTEM_PROMPT = """You are a precise answer synthesis expert. You are given a 
user question and retrieved document chunks. Your job is to write a clear, 
accurate answer based strictly on the retrieved content.

Rules:
1. Answer ONLY from the retrieved content. Never use outside knowledge.
2. Cite the source document title for every claim, like this: (Source: Document Title)
3. If the retrieved content does not contain enough information to answer the 
   question, respond with exactly: 
   "I could not find an answer in the available documents."
4. Be concise. Do not pad the answer with unnecessary explanation.
5. If multiple documents contributed to the answer, cite each one.
"""


def synthesize(question: str, retrieved_context: str) -> str:
    """
    Takes the original question and all retrieved chunks.
    Returns a grounded answer with citations.
    """
    print(f"  [Synthesizer] Writing answer from retrieved context")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"User question: {question}\n\n"
                f"Retrieved content:\n{retrieved_context}"
            ),
        },
    ]

    answer = _call_llm(messages)
    print(f"  [Synthesizer] Done")
    return answer


def _call_llm(messages: list[dict]) -> str:
    if PROVIDER == "anthropic":
        import anthropic as ac
        anth     = ac.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = anth.messages.create(
            model=CHAT_MODEL,
            max_tokens=1024,
            system=messages[0]["content"],
            messages=messages[1:],
        )
        return response.content[0].text

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        max_tokens=1024,
    )
    return response.choices[0].message.content