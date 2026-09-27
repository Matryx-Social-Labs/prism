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
