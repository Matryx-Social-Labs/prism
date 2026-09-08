"""Role-aware suggested questions per story (docs/AGENT.md).

Static templates from the lens registry, tuned by event shape — no LLM
spend per view. The user's lens wins when the story carries its fields;
otherwise fall back to whichever lens the story evidences.
"""

from common.lenses import LENSES, get_lens


def suggested_questions(
    projection: dict | None,
    lens_slug: str | None = None,
    *,
    unlocked: bool = False,
) -> list[str]:
    projection = projection or {}
    cyber = projection.get("cyber")
    finance = projection.get("finance")

    lens = get_lens(lens_slug)
    # If the user's lens has no fields on this story, show the story's own lens.
    if lens.slug == "cyber" and not cyber and finance:
        lens = LENSES["markets"]
    elif lens.slug == "markets" and not finance and cyber:
        lens = LENSES["cyber"]
    elif lens.slug != "reader" and not cyber and not finance:
        lens = LENSES["reader"]

    questions = list(lens.suggested_questions)
    # THE ONLY QUESTION DERIVED FROM STORY DATA, so the only one that can leak.
    # `GET /events/{id}` filters `projection` to unlocked lenses; this route
    # reads the same field unfiltered, so before the gate an anonymous caller
    # could loop every event with ?lens=cyber and read off the KEV set from
    # question 1 alone. Low-value on its own (CISA publishes KEV free) but it is
    # an oracle over gated data, and two routes disagreeing about one field is
    # exactly what made /brief bypassable.
    #
    # It is also the better funnel: "How is this being exploited in the wild?"
    # answers itself. The free reader gets "Is it being actively exploited?" —
    # the question is the upsell, the answer is the product.
    #
    # Fail closed: `unlocked` defaults False, so a caller that forgets to pass
    # it leaks nothing.
    if (
        unlocked
        and lens.slug == "cyber"
        and (cyber or {}).get("exploitation", {}).get("kev_listed")
    ):
        questions[1] = "How is this being exploited in the wild?"
    return questions
