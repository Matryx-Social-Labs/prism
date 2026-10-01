"""A record's place in time: when it was first reported, and which way its links run.

`events.first_seen_at` is when Prism processed the founding article. After a
backlog that is hours late and in processing order: on 2026-10-01 the Flydubai
cockpit-attack story (190 articles published from 09-30 07:30 UTC) became 70
records all first seen 10-01 08:18-12:14, and every timeline ordered by it read
in the order the queue drained. `occurred_at` is the extractor's date: no time,
missing on ~40% of records, sometimes a day off.

`first_published_at` is the earliest member article's own publication time, so
it moves when an earlier report joins or a merge brings one in, and a leads_to
link written the right way round can end up backwards. Both are therefore kept
here, on every projection rebuild (consumer._rebuild_projection, which every
attach, merge and repair goes through), and wherever a link is written.
"""

import uuid

from sqlalchemy import text

# A report's own date counts only inside a week before Prism first saw the
# record and an hour after: RSS dates can be bogus, a live blog carrying the
# date of its first post months back, or a time in the future (an IST clock
# labelled UTC is 5h30 ahead). Outside the window, first_seen_at stands.
FIRST_PUBLISHED = """COALESCE((
    SELECT min(ri.published_at)
    FROM event_memberships em
    JOIN articles a ON a.id = em.article_id
    JOIN raw_items ri ON ri.id = a.raw_item_id
    WHERE em.event_id = e.id
      AND ri.published_at BETWEEN e.first_seen_at - interval '7 days' AND e.first_seen_at + interval '1 hour'
), e.first_seen_at)"""


def _orient(scope: str):
    # A leads_to link runs from the earlier record to the later one. A tie keeps
    # the writer's direction. A pair stored both ways round is left alone
    # (ponytail: 5 of 2,668 thread links on 2026-10-01; the unique pair blocks
    # the flip, and deciding which of the two to drop is not this rule's call).
    return text(
        f"""
        UPDATE event_links l SET from_event_id = l.to_event_id, to_event_id = l.from_event_id
        FROM events f, events t
        WHERE l.relation = 'leads_to' AND {scope}
          AND f.id = l.from_event_id AND t.id = l.to_event_id
          AND COALESCE(f.first_published_at, f.first_seen_at) > COALESCE(t.first_published_at, t.first_seen_at)
          AND NOT EXISTS (SELECT 1 FROM event_links r
                          WHERE r.from_event_id = l.to_event_id AND r.to_event_id = l.from_event_id)
        """
    )


ORIENT_ONE = _orient("(l.from_event_id = :eid OR l.to_event_id = :eid)")
ORIENT_ALL = _orient("true")

_migrated = False


async def migrated(session) -> bool:
    """Whether events.first_published_at exists yet. Only the API container
    migrates (Dockerfile CMD), so a worker on this code can start first, and a
    statement naming the column would then fail every attach: the verified tier
    stalled exactly so on 2026-09-29. Asked until the answer is yes."""
    global _migrated
    if not _migrated:
        _migrated = (
            await session.execute(
                text("SELECT 1 FROM information_schema.columns "
                     "WHERE table_name = 'events' AND column_name = 'first_published_at'")
            )
        ).first() is not None
    return _migrated


async def place_in_time(session, event_id: uuid.UUID) -> None:
    """Set the record's first_published_at from its members, then turn any
    leads_to link touching it the right way round."""
    if not await migrated(session):
        return
    await session.execute(
        text(f"UPDATE events e SET first_published_at = {FIRST_PUBLISHED} WHERE e.id = :eid"),
        {"eid": str(event_id)},
    )
    await session.execute(ORIENT_ONE, {"eid": str(event_id)})
