# evals/judge.py

import json
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

JUDGE_PROMPT = """You are a strict answer quality judge. You will be given a 
question, a reference answer, and an agent's answer. Score the agent's answer.

Scoring criteria:
- Score 1 if the agent's answer contains the key facts from the reference answer,
  even if worded differently.
- Score 0 if the agent's answer is missing key facts, contains wrong information,
  or says it cannot find the answer when a reference answer exists.
- Score 0 if the agent's answer contains hallucinated facts not in the reference.

Return ONLY a JSON object with exactly these two fields:
{"score": 0 or 1, "reason": "one sentence explanation"}

No preamble. No markdown. Just the JSON object.
"""


def judge_answer(
    question: str,
    reference_answer: str,
    agent_answer: str,
) -> dict:
    """
    Scores an agent answer against a reference answer.
    Returns {"score": 0|1, "reason": str}
    """
    messages = [
        {"role": "system", "content": JUDGE_PROMPT},
        {
            "role": "user",
            "content": (
                f"Question: {question}\n\n"
                f"Reference answer: {reference_answer}\n\n"
                f"Agent answer: {agent_answer}"
            ),
        },
    ]

    response = _call_llm(messages)
    return _parse_result(response)


def judge_abstention(agent_answer: str) -> dict:
    """
    Checks whether the agent correctly abstained on an unanswerable question.
    Returns {"score": 0|1, "reason": str}
    """
    ABSTENTION_MARKERS = [
        "could not find",
        "cannot find",
        "not available",
        "no information",
        "don't have",
        "do not have",
        "not in the",
        "unable to find",
        "not found",
    ]

    answer_lower = agent_answer.lower()
    abstained    = any(marker in answer_lower for marker in ABSTENTION_MARKERS)

    if abstained:
        return {"score": 1, "reason": "Agent correctly abstained"}
    return {"score": 0, "reason": f"Agent did not abstain. Said: '{agent_answer[:80]}'"}


def judge_citation(
    agent_answer: str,
    expected_sources: list[str],
) -> dict:
    """
    Checks whether the agent cited at least one expected source document.
    Returns {"score": 0|1, "reason": str}
    """
    if not expected_sources:
        return {"score": 1, "reason": "No sources expected"}

    answer_lower = agent_answer.lower()
    for source in expected_sources:
        if source.lower() in answer_lower:
            return {"score": 1, "reason": f"Cited '{source}'"}

    return {
        "score": 0,
        "reason": f"Expected citation for {expected_sources} not found in answer",
    }


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


def _parse_result(response: str) -> dict:
    """
    Parse JSON from judge response.
    Falls back to score=0 if parsing fails — we never silently pass a bad answer.
    """
    try:
        clean  = response.strip().strip("```json").strip("```").strip()
        result = json.loads(clean)

        # Normalize keys to lowercase — Mistral sometimes capitalizes them
        result = {k.lower(): v for k, v in result.items()}

        if "score" in result and "reason" in result:
            return {"score": int(result["score"]), "reason": result["reason"]}

    except (json.JSONDecodeError, ValueError, KeyError):
        pass

    return {"score": 0, "reason": f"Judge returned unparseable response: {response[:80]}"}