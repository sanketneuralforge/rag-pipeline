# agents/synthesizer.py

from openai import OpenAI
from config import (
    PROVIDER,
    OLLAMA_BASE_URL,
    OPENAI_API_KEY, OPENAI_CHAT_MODEL,
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
    FAST_MODEL, CAPABLE_MODEL,
    COMPLEX_QUERY_KEYWORDS,
    STREAM_ENABLED,
)

if PROVIDER == "ollama":
    client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
elif PROVIDER == "openai":
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    client = None

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
    Synthesizes a grounded answer with citations.
    Routes to FAST or CAPABLE model based on question complexity.
    Streams output if STREAM_ENABLED is True.
    """
    model = _route_model(question, retrieved_context)
    print(f"  [Synthesizer] Model: {model} | Stream: {STREAM_ENABLED}")

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

    if PROVIDER == "anthropic":
        return _call_anthropic(messages, model)

    if STREAM_ENABLED:
        return _call_streaming(messages, model)

    return _call_standard(messages, model)


def _route_model(question: str, retrieved_context: str) -> str:
    """
    Decides which model to use based on question complexity.

    Simple questions → FAST_MODEL  (cheap, low latency)
    Complex questions → CAPABLE_MODEL (better reasoning)

    Complexity signals:
    1. Question contains complexity keywords (compare, summarize, explain...)
    2. Retrieved context contains chunks from multiple source documents
    """
    question_lower = question.lower()

    # Signal 1: complexity keywords in question
    has_complex_keyword = any(
        kw in question_lower for kw in COMPLEX_QUERY_KEYWORDS
    )

    # Signal 2: multiple source documents in retrieved context
    import re
    sources = set(re.findall(r"Source:\s*([^\n(]+?)(?:\s*\(|$)", retrieved_context))
    is_multi_doc = len(sources) >= 2

    if has_complex_keyword or is_multi_doc:
        print(f"  [Synthesizer] Routing → CAPABLE model "
              f"(keyword={has_complex_keyword}, multi_doc={is_multi_doc})")
        return CAPABLE_MODEL

    print(f"  [Synthesizer] Routing → FAST model")
    return FAST_MODEL


def _call_streaming(messages: list[dict], model: str) -> str:
    """
    Streams tokens as they are generated.
    Prints each token immediately — user sees output start in ~1s.
    Collects and returns the full answer at the end.
    """
    print("  [Synthesizer] Streaming: ", end="", flush=True)

    full_answer = []

    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=1024,
        stream=True,        # ← the key parameter
    )

    for chunk in stream:
        token = chunk.choices[0].delta.content
        if token:
            print(token, end="", flush=True)   # print immediately, no newline
            full_answer.append(token)

    print()   # newline after streaming completes
    return "".join(full_answer)


def _call_standard(messages: list[dict], model: str) -> str:
    """Non-streaming fallback."""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=1024,
    )
    return response.choices[0].message.content


def _call_anthropic(messages: list[dict], model: str) -> str:
    """Anthropic streaming via native client."""
    import anthropic as ac
    anth = ac.Anthropic(api_key=ANTHROPIC_API_KEY)

    if STREAM_ENABLED:
        print("  [Synthesizer] Streaming: ", end="", flush=True)
        full_answer = []

        with anth.messages.stream(
            model=model,
            max_tokens=1024,
            system=messages[0]["content"],
            messages=messages[1:],
        ) as stream:
            for token in stream.text_stream:
                print(token, end="", flush=True)
                full_answer.append(token)

        print()
        return "".join(full_answer)

    response = anth.messages.create(
        model=model,
        max_tokens=1024,
        system=messages[0]["content"],
        messages=messages[1:],
    )
    return response.content[0].text