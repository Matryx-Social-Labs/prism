"""Role-aware suggested questions per story (docs/AGENT.md).

Static templates keyed on lens/event shape — no LLM spend per view.
"""

CYBER_QUESTIONS = [
    "Does this affect my stack?",
    "Is it being actively exploited?",
    "What should I patch or mitigate?",
    "Which of my controls does this touch?",
]

GENERAL_QUESTIONS = [
    "What led to this?",
    "Who is affected?",
    "What are the likely outcomes?",
    "How is each side framing it?",
]


def suggested_questions(projection: dict | None) -> list[str]:
    cyber = (projection or {}).get("cyber")
    if cyber:
        questions = list(CYBER_QUESTIONS)
        exploitation = cyber.get("exploitation") or {}
        if exploitation.get("kev_listed"):
            questions[1] = "How is this being exploited in the wild?"
        return questions
    return list(GENERAL_QUESTIONS)
