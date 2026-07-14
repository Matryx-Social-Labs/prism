"""Role-aware suggested questions per story (docs/AGENT.md).

Static templates from the lens registry, tuned by event shape — no LLM
spend per view. The user's lens wins when the story carries its fields;
otherwise fall back to whichever lens the story evidences.
"""

from common.lenses import LENSES, get_lens


def suggested_questions(projection: dict | None, lens_slug: str | None = None) -> list[str]:
    projection = projection or {}
    cyber = projection.get("cyber")
    finance = projection.get("finance")

    lens = get_lens(lens_slug)
    # If the user's lens has no fields on this story, show the story's own lens.
    if lens.slug == "cyber_grc" and not cyber and finance:
        lens = LENSES["finance_trader"]
    elif lens.slug == "finance_trader" and not finance and cyber:
        lens = LENSES["cyber_grc"]
    elif lens.slug != "general" and not cyber and not finance:
        lens = LENSES["general"]

    questions = list(lens.suggested_questions)
    if lens.slug == "cyber_grc" and (cyber or {}).get("exploitation", {}).get("kev_listed"):
        questions[1] = "How is this being exploited in the wild?"
    return questions
