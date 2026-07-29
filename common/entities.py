"""Which extracted names are allowed to become entities.

The extractor faithfully returns the outlet as an actor — a Kannada article that
opens "ಟಿವಿ9 ಕನ್ನಡ ವರದಿ" yields `tv9kannada`, and a byline yields `prajavani`.
Persisted, those become the most-connected nodes in the graph, and they are the
one thing every article from a source has in common. Two consequences, both
measured on production 2026-07-28:

  - `prajavani` was the single most-shared "entity" across the 139 articles of one
    over-merged event — the outlet, doing the merging.
  - `tv9kannada` was the FIRST cast name on a live trending story, so the product
    told readers the story was about a television channel.

An outlet is not an actor in its own coverage. Filtered at the choke point that
both persists entities and feeds the clustering gate, so the two cannot disagree.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.text import entity_slug

# Cached per process: sources change when someone edits a seed file, not at runtime.
_cache: set[str] | None = None


async def source_name_slugs(session: AsyncSession) -> set[str]:
    """Entity slugs that are really outlet names — both the registry slug and the
    display name, since the extractor emits the prose form ('TV9 Kannada') while
    the registry holds the handle ('tv9kannada')."""
    global _cache
    if _cache is None:
        rows = (await session.execute(text("SELECT slug, name FROM sources"))).all()
        out: set[str] = set()
        for slug, name in rows:
            for v in (slug, name):
                if v:
                    out.add(entity_slug(v))
                    # 'The Hindu' also arrives as 'Hindu'; 'TV9 Kannada' as 'TV9'.
                    head = str(v).split()[0]
                    if len(head) > 3:
                        out.add(entity_slug(head))
        _cache = out
    return _cache


def reset_cache() -> None:
    """Tests seed sources mid-run; the process cache would otherwise pin an empty set."""
    global _cache
    _cache = None


async def drop_source_names(session: AsyncSession, names: list[str]) -> list[str]:
    """`names` minus anything that is really an outlet."""
    blocked = await source_name_slugs(session)
    return [n for n in names if entity_slug(n) not in blocked]
