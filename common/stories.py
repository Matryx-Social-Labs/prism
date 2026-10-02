"""What a story (a trending arc) may claim about itself. Read by the API that
serves stories and by the worker that announces them to search engines, so the
two cannot disagree."""

# Promotion is a deliberate code/config change after the time-held-out,
# two-labeller story evaluation passes. Until then no story claims verified
# chronology: the API serves no route tree a client could mistake for one, and
# no story asks to be indexed — a provisional grouping drifts, and four of them
# sat in Search Console's "crawled - currently not indexed" with URLs promising
# one event and pages showing another (2026-09-21).
STORY_BOUNDARY_STATUS = "provisional"


def boundary_status(anchor_event_id) -> str:
    """A story the judge built (correlation/stories.py: every record confirmed part
    of it at birth; 0.93-0.98 of joins right on 60 read blind, 2026-10-02) is
    verified. A Leiden grouping keeps STORY_BOUNDARY_STATUS."""
    return "verified" if anchor_event_id else STORY_BOUNDARY_STATUS
