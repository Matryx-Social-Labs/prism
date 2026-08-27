"""Streams must be bounded. Redis does NOT drop entries on XACK.

An acknowledged message stays in the stream forever unless something trims it,
and nothing did. Measured in production: 306,509 entries across five topics —
raw.items alone at 141,185, and event.updates at 65,736 with ZERO consumer
groups, meaning nothing had ever read one of them.

The failure mode is the reason this needs a test rather than a comment: there is
no symptom at all until Redis reaches its memory limit, at which point the whole
pipeline stops at once.
"""

import inspect

import common.stream as stream


def test_publish_bounds_the_stream():
    src = inspect.getsource(stream.publish)
    assert "maxlen" in src, "xadd without maxlen grows the stream without bound"
    assert "approximate=True" in src, (
        "exact trimming is far more expensive per write; radix-boundary "
        "trimming is the right trade for a hot path"
    )


def test_the_cap_leaves_room_for_a_lagging_consumer():
    """A consumer reclaiming after a crash may be up to STALE_CLAIM_IDLE_MS
    behind. The cap has to dwarf what can accumulate in that window — roughly
    1k items per 30-minute ingest run."""
    assert stream.STREAM_MAXLEN >= 50_000


def test_the_cap_is_tunable_without_a_deploy():
    assert "PRISM_STREAM_MAXLEN" in inspect.getsource(stream)


def test_the_unread_topic_is_gone():
    """event.updates was published twice per event and consumed by nobody:
    65,736 entries, zero consumer groups. A topic with no reader is not an
    extension point, it is a leak."""
    assert not hasattr(stream, "EVENT_UPDATES")
    assert not hasattr(stream, "EVENTS"), "declared and never published"


def test_the_live_topics_are_still_declared():
    """Counterpart — deleting the dead ones must not take the real ones."""
    for topic in ("RAW_ITEMS", "CLASSIFIED_ITEMS", "ENRICHED_ITEMS", "ADMIN_TRIGGERS"):
        assert hasattr(stream, topic), f"{topic} is a live topic and must survive"
