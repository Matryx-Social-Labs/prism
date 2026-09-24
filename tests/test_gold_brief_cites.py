"""The brief_support rounds are answered by construction, never by opinion.

tools/gold_brief_cites builds the practice round and the qualification test with
no labelled gold: YES is the report's own sentence; NO is a sentence with one
figure changed to a number the report never prints, a claim appended the report
never makes, or another story's sentence. Pinned: each construction is what it
claims to be, and a pool is half and half.
"""

import random
import uuid

from correlation.cites import figures
from tools.gold_brief_cites import add_claim, construct, excerpt, swap_figure

REPORT = ("The Reserve Bank of India kept the repo rate unchanged at 5.5 per cent on Wednesday after a three-day meeting. "
          "Governor Sanjay Malhotra said inflation had eased to 2.1 per cent in August from 3.2 per cent in July. "
          "The committee voted 4 to 2 to keep the stance neutral, with two members arguing for a cut. "
          "Markets had expected the pause, and the rupee closed little changed against the dollar in Mumbai trade.")
OTHER = ("Heavy rain flooded low-lying neighbourhoods across Chennai overnight and several suburban trains were cancelled. "
         "Rescue teams moved families from riverside homes to relief camps set up in schools and community halls. "
         "Officials warned that the downpour could continue through the weekend along the northern coast of the state.")


def test_a_swapped_figure_is_one_the_report_never_prints():
    s = "Governor Sanjay Malhotra said inflation had eased to 2.1 per cent in August from 3.2 per cent in July."
    changed, old, new = swap_figure(s, REPORT, random.Random(1))
    assert old in s and new in changed and old != new
    assert new.replace(",", "") not in figures(REPORT)


def test_an_appended_claim_is_one_the_report_never_makes():
    s = "The committee voted 4 to 2 to keep the stance neutral, with two members arguing for a cut."
    changed, extra = add_claim(s, REPORT, random.Random(2))
    assert changed.startswith(s[:-1]) and extra in changed and extra.lower() not in REPORT.lower()


def test_the_excerpt_is_the_passage_the_line_comes_from():
    assert "inflation had eased to 2.1 per cent" in excerpt("Inflation eased to 2.1% in August.", REPORT)


def test_construction_gives_true_yes_and_true_no_items():
    reports = [
        {"event_id": uuid.uuid4(), "event_title": "Rates held", "clean_text": REPORT, "title": "RBI holds",
         "source": "Mint", "language_name": "English", "lang": "en", "url": None},
        {"event_id": uuid.uuid4(), "event_title": "Chennai floods", "clean_text": OTHER, "title": "Rain",
         "source": "The Hindu", "language_name": "English", "lang": "en", "url": None},
    ]
    items = construct(reports, random.Random(3))
    mine = [it for it in items if it["payload"]["story"] == "Rates held"]
    yes = [it for it in mine if it["yes"]]
    no = [it for it in mine if not it["yes"]]
    assert yes and no
    for it in yes:
        assert it["payload"]["line"] in REPORT, "a YES is the report's own sentence"
    for it in no:
        assert it["payload"]["line"] not in REPORT, "a NO is never a sentence of the report"
        assert it["explanation"]
    assert all(it["payload"]["kind"] == "brief_support" and it["languages"] == ["en"] for it in items)
