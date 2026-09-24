"""Two small holes measured on production, both silent.

1. The CVE lens builds its summary straight from raw NVD JSON and never passed
   through ingestion/base.py's clean_text choke point, so 9 event summaries
   created AFTER that fix still carried HTML entities.
2. BleepingComputer 403d on every 30-minute cycle since ingestion began, emitting
   a traceback each time.
"""

import pytest

from enrichment.cve_lens import extract_from_nvd
from ingestion.rss import FEEDS, USER_AGENT


def _nvd(desc: str) -> dict:
    return {"id": "CVE-2026-0001", "descriptions": [{"lang": "en", "value": desc}]}


@pytest.mark.parametrize(
    "raw,gone",
    [
        ("Foo &amp; bar", "&amp;"),
        ("a &quot;quoted&quot; value", "&quot;"),
        ("non&nbsp;breaking", "&nbsp;"),
        ("O&#039;Brien reported", "&#039;"),
    ],
)
def test_cve_summaries_do_not_ship_html_entities(raw, gone):
    summary = extract_from_nvd(_nvd(raw)).shared.headline_summary
    assert gone not in summary


def test_the_cve_fix_unescapes_but_does_not_strip_markup():
    """unescape, not clean_text. A CVE description quotes the markup it is ABOUT —
    a real production summary explains that an endpoint returns an inline <script>
    snippet — and clean_text strips tags, which deletes the vulnerability being
    described.

    The literal form is what separates them, and that is worth stating because my
    first cut of this test used the ESCAPED form and was vacuous: clean_text
    strips tags before unescaping, so with &lt;script&gt; there is no tag present
    yet and both functions return the same string. Only literal markup tells them
    apart."""
    summary = extract_from_nvd(
        _nvd("The endpoint returns an inline <script>alert(1)</script> snippet")
    ).shared.headline_summary
    assert "<script>" in summary, "markup the CVE is about was stripped"


def test_an_empty_description_does_not_crash_or_leak_none():
    summary = extract_from_nvd({"id": "CVE-2026-0002", "descriptions": []}).shared.headline_summary
    assert "CVE-2026-0002" in summary and "None" not in summary


def test_a_feed_blocked_at_the_egress_is_not_fetched_every_cycle():
    off = [f.slug for f in FEEDS if not f.enabled]
    assert "bleepingcomputer" in off, "the dead feed is being fetched again"


def test_every_other_feed_stays_on():
    """A disable flag is a trapdoor — one stray default and ingestion goes quiet."""
    on = [f.slug for f in FEEDS if f.enabled]
    # Every feed that is off is off for a measured reason written beside it.
    assert {f.slug for f in FEEDS if not f.enabled} == {"bleepingcomputer", "pib", "sebi"}
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
