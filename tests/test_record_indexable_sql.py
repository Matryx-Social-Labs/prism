"""The record rule in SQL must say what common/outlets.record_indexable says: an
actor page counts only the records that are themselves indexed, and the SQL is
how the chips, the page and the sitemap ask."""

import json
import uuid

import pytest
from sqlalchemy import text

from common import outlets
from common.db import session_scope
from common.outlets import record_indexable, record_indexable_sql
from tests.test_entity_page import _db_reachable

pytestmark = pytest.mark.asyncio(loop_scope="session")

CASES = [
    [],
    ["t_hindu"],
    ["t_hindu", "t_ndtv"],
    ["t_bbc_hindi", "t_bbc_tamil"],  # one publisher's language editions are one outlet
    ["t_bbc_hindi", "t_hindu"],
    ["nvd", "cisa_kev"],  # raw-record feeds are not outlets
    ["nvd", "t_hindu"],
    ["t_hindu", "unregistered_feed"],  # registered sources win when there are any
    ["unregistered_a", "unregistered_b"],  # none registered: counted by slug
]


def test_the_rule_takes_an_alias_never_a_value():
    assert "e.projection" in record_indexable_sql("e")
    with pytest.raises(ValueError):
        record_indexable_sql("e; DROP TABLE events")


async def test_the_sql_says_what_the_python_says():
    if not await _db_reachable():
        pytest.skip("no database")
    feeds = {"t_hindu": "The Hindu", "t_ndtv": "NDTV", "t_bbc_hindi": "BBC", "t_bbc_tamil": "BBC"}
    async with session_scope() as s:
        for slug, publisher in feeds.items():
            await s.execute(
                text(
                    "INSERT INTO sources (id, slug, name, source_type, publisher) VALUES (:i, :s, :s, 'rss', :p) "
                    "ON CONFLICT (slug) DO NOTHING"
                ),
                {"i": str(uuid.uuid4()), "s": slug, "p": publisher},
            )
    try:
        outlets._cache = None
        async with session_scope() as s:
            reg = await outlets.registry(s)
            for slugs in CASES:
                got = (
                    await s.execute(
                        text(
                            f"SELECT {record_indexable_sql('e')} FROM (SELECT CAST(:p AS jsonb) AS projection) e"
                        ),
                        {"p": json.dumps({"source_slugs": slugs})},
                    )
                ).scalar_one()
                assert got is record_indexable(slugs, reg), slugs
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM sources WHERE slug = ANY(:s)"), {"s": list(feeds)})
        outlets._cache = None
