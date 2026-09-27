"""The feed registry's hygiene: what is on, what is off and why, and that every
feed can actually be fetched and attributed."""

import pytest

from ingestion.rss import FEEDS, SPEC_BY_SLUG, USER_AGENT

# Founder, 2026-09-27: cyber and tech come from news that reports a story, never
# vulnerability-record feeds. Each verified 200 with recent items, with this
# User-Agent, from the worker's own egress (docs/DATA-SOURCES.md).
CYBER_AND_TECH_NEWS = (
    "ettech", "etciso", "medianama", "inc42", "entrackr", "thehindu_technology", "livemint_technology",
    "thehackernews", "bleepingcomputer", "therecord", "securityweek", "krebsonsecurity", "cyberscoop",
    "theregister_security",
)


@pytest.mark.parametrize("slug", CYBER_AND_TECH_NEWS)
def test_cyber_and_tech_come_from_news_feeds_the_classifier_reads(slug):
    """On, and never declared single-topic: a declared sector skips the gate and
    the classifier, which is how three general feeds filed a campus protest as
    business."""
    assert SPEC_BY_SLUG[slug].enabled and SPEC_BY_SLUG[slug].sector is None


def test_every_other_feed_stays_on():
    """A disable flag is a trapdoor — one stray default and ingestion goes quiet."""
    on = [f.slug for f in FEEDS if f.enabled]
    # Every feed that is off is off for a measured reason written beside it.
    assert {f.slug for f in FEEDS if not f.enabled} == {"pib", "sebi", "businessstandard"}
    for core in ("thehindu", "timesofindia", "ndtv", "thehackernews", "rbi"):
        assert core in on


def test_a_bare_rfc822_date_is_read_as_ist():
    """RBI prints its wall clock with no zone; feedparser leaves published_parsed
    empty and every RBI release would have carried no date at all."""
    from datetime import UTC, datetime

    from ingestion.rss import _entry_datetime

    when = _entry_datetime({"published": "Mon, 21 Sep 2026 14:30:00"})
    assert when == datetime(2026, 9, 21, 9, 0, tzinfo=UTC)
    # A zoned date still goes through feedparser's struct_time, untouched.
    import time

    zoned = _entry_datetime({"published_parsed": time.gmtime(1_790_000_000)})
    assert zoned == datetime.fromtimestamp(1_790_000_000, tz=UTC)
    assert _entry_datetime({"published": "not a date"}) is None
    assert _entry_datetime({}) is None


def test_the_crawler_identifies_itself_and_is_reachable():
    assert "prototype" not in USER_AGENT.lower()
    assert "readprism.news" in USER_AGENT


def test_regional_editions_fold_into_one_masthead():
    """REGRESSION: The Times of India counted as three publishers.

    `sources.publisher` exists so corroboration counts MASTHEADS, not feeds —
    correlation/trending.py and correlation/consumer.py both read
    `COALESCE(s.publisher, s.slug)`. bbc_* and thehindu_* were seeded with one;
    toi_delhi and toi_mumbai were not, so they coalesced to their own slugs and
    one newsroom republishing itself across its city feeds read as independent
    corroboration. 800 production URLs arrived under more than one source.

    The failure is invisible: a story shows a larger source count and stops
    flagging `single_origin`, which is precisely the "only one newsroom is
    telling you this" warning a reader most needs.
    """
    from ingestion.seed import SOURCES

    groups: dict[str, list[dict]] = {}
    for src in SOURCES:
        groups.setdefault(src["slug"].split("_")[0], []).append(src)

    for prefix, siblings in groups.items():
        if len(siblings) < 2:
            continue  # not a family of regional editions
        # This is exactly what the SQL computes.
        publishers = {s.get("publisher") or s["slug"] for s in siblings}
        assert len(publishers) == 1, (
            f"{prefix}_* is one masthead across {len(siblings)} feeds but resolves to "
            f"{len(publishers)} publishers {sorted(publishers)} — corroboration will "
            "count this newsroom republishing itself as independent sources"
        )


def test_every_feed_has_a_seed_row_and_a_language_name():
    """A feed URL lives in ingestion/rss.py and its outlet row in ingestion/seed.py.
    A FeedSpec without a seed row raises "source not seeded" on every cycle; a
    seeded language missing from common/languages.py prints as a bare code on
    every quote. The 2026-09-24 expansion added 19 outlets across both files and
    three new languages (Malayalam, Odia, Assamese)."""
    from common.languages import LANGUAGES
    from ingestion.seed import SOURCES

    seeded = {s["slug"]: s for s in SOURCES}
    unseeded = [f.slug for f in FEEDS if f.slug not in seeded]
    assert not unseeded, f"feeds with no seed row: {unseeded}"
    assert len({f.slug for f in FEEDS}) == len(FEEDS), "a feed slug is listed twice"
    unnamed = sorted({seeded[f.slug]["language"] for f in FEEDS} - set(LANGUAGES))
    assert not unnamed, f"languages with no display name: {unnamed}"
