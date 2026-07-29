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
    assert len(on) == len(FEEDS) - 1
    for core in ("thehindu", "timesofindia", "ndtv", "thehackernews"):
        assert core in on


def test_the_crawler_identifies_itself_and_is_reachable():
    assert "prototype" not in USER_AGENT.lower()
    assert "readprism.news" in USER_AGENT
