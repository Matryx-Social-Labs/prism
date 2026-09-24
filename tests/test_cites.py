"""Each line of a brief points at the report it restates; its figures must be there.

Shadow layer for the trust plan's Phase 2 (correlation/cites.py). Pinned: the
split matches the page's, a single-report record cites that report by
construction, a multi-report record cites the report whose words carry the
line, an Indian-language report is cited by the figures it shares, and a figure
no cited report contains marks the line unsupported: the one thing a brief must
never do.
"""

import json
import uuid

import pytest
from sqlalchemy import text

from correlation.cites import cite_lines, figures, split_lines

pytestmark = pytest.mark.asyncio(loop_scope="session")

A, B, C = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


def test_the_split_matches_the_page_initials_and_abbreviations_are_not_ends():
    brief = "N. Chandrasekaran chairs Tata Sons. The group paid Rs. 1,200 crore. It matters for jobs."
    assert split_lines(brief) == [
        "N. Chandrasekaran chairs Tata Sons.",
        "The group paid Rs. 1,200 crore.",
        "It matters for jobs.",
    ]


def test_figures_read_indian_digits_and_thousands_separators_as_the_same_number():
    assert figures("रेपो दर ५.५ प्रतिशत, ₹1,200 करोड़") == {"5.5", "1200"}
    assert figures("The rate stayed at 5.5%.") == {"5.5"}


def test_one_report_is_cited_by_construction_and_a_figure_it_lacks_is_unsupported():
    report = [(A, "The Reserve Bank kept the repo rate at 5.5% on Wednesday.")]
    lines = cite_lines("The RBI held the repo rate at 5.5%. It raised it to 6.25%.", report)
    assert [(ln["cites"], ln["method"], ln["supported"]) for ln in lines] == [
        ([str(A)], "single", True),
        ([str(A)], "single", False),
    ]


def test_many_reports_cite_the_one_whose_words_carry_the_line():
    reports = [
        (A, "Flood waters rose in Assam districts; relief camps opened for displaced families."),
        (B, "The finance minister announced a revised fiscal deficit target for the year."),
    ]
    [flood, deficit] = cite_lines(
        "Relief camps opened for displaced families in Assam. The finance minister revised the fiscal deficit target.",
        reports,
    )
    assert flood["cites"] == [str(A)] and flood["method"] == "lexical" and flood["supported"]
    assert deficit["cites"] == [str(B)] and deficit["supported"]


def test_an_indian_language_report_is_cited_by_the_figures_it_shares():
    reports = [
        (A, "Unrelated English report about cricket selections for the tour."),
        (C, "राज्य में बाढ़ से १२ लोगों की मौत, ३४० गांव प्रभावित"),
    ]
    [line] = cite_lines("Floods killed 12 people and hit 340 villages.", reports)
    assert (line["cites"], line["method"], line["supported"]) == ([str(C)], "figures", True)


def test_a_line_no_report_supports_cites_nothing():
    reports = [(A, "Cricket selectors named the squad."), (B, "Monsoon arrived early in Kerala.")]
    [line] = cite_lines("Parliament passed the data protection amendment.", reports)
    assert (line["cites"], line["method"], line["supported"]) == ([], "none", False)


async def test_saving_a_reader_brief_stores_its_citations_beside_it():
    from common.db import session_scope
    from correlation.briefs import persist_briefs
    from tests.test_projection_summary import _add_member, _db_reachable

    if not await _db_reachable():
        pytest.skip("no database")
    eid, src = uuid.uuid4(), uuid.uuid4()
    created = []
    try:
        async with session_scope() as s:
            await s.execute(text("INSERT INTO sources (id, slug, name, source_type, country, publisher) "
                                 "VALUES (:i, :s, 'Cites Test', 'rss', 'IN', 'cites-test')"),
                            {"i": str(src), "s": f"cites-{eid.hex[:8]}"})
            await s.execute(text("INSERT INTO events (id, title, summary, last_updated_at) VALUES (:i, 't', 's', now())"),
                            {"i": str(eid)})
            created.append(await _add_member(s, eid, title="The repo rate stayed at 5.5 percent", summary="s", source_id=src))
        await persist_briefs(eid, {"reader": "The repo rate stayed at 5.5 percent. It was cut to 4 percent."})
        async with session_scope() as s:
            proj = (await s.execute(text("SELECT projection FROM events WHERE id = :i"), {"i": str(eid)})).scalar_one()
        art = str(created[0][1])
        assert proj["lens_cites"]["reader"] == [
            {"text": "The repo rate stayed at 5.5 percent.", "cites": [art], "method": "single", "supported": True},
            {"text": "It was cut to 4 percent.", "cites": [art], "method": "single", "supported": False},
        ]
        assert json.dumps(proj["lens_briefs"]).count("repo rate") == 1
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_memberships WHERE event_id = :e"), {"e": str(eid)})
            for raw_id, art_id in created:
                await s.execute(text("DELETE FROM enrichments WHERE article_id = :a"), {"a": str(art_id)})
                await s.execute(text("DELETE FROM articles WHERE id = :a"), {"a": str(art_id)})
                await s.execute(text("DELETE FROM raw_items WHERE id = :r"), {"r": str(raw_id)})
            await s.execute(text("DELETE FROM events WHERE id = :e"), {"e": str(eid)})
            await s.execute(text("DELETE FROM sources WHERE id = :s"), {"s": str(src)})
