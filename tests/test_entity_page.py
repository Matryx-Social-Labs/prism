"""Audit H29: the actor pages the cast chips point at. A page exists for every
entity on a record; only one with enough records asks to be indexed."""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from api.routes.entity import INDEXABLE_MIN_RECORDS, schema_type
from common.db import session_scope
from common.models import Entity, Event, EventEntity


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("person", "Person"),
        ("company", "Organization"),
        ("government", "GovernmentOrganization"),
        ("place", "Place"),
        # Production's own junk types, which must not assert something false.
        ("government|subject", "GovernmentOrganization"),
        ("org  anization", "Thing"),
        ("personist|personrole|subjectaffected", "Thing"),
        (None, "Thing"),
    ],
)
def test_the_extractors_loose_vocabulary_maps_to_schema_or_thing(raw, expected):
    assert schema_type(raw) == expected


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _seed(n_records: int) -> str:
    slug = f"t-{uuid.uuid4().hex[:10]}"
    async with session_scope() as s:
        ent = Entity(id=uuid.uuid4(), slug=slug, name="Test Actor", entity_type="person")
        s.add(ent)
        await s.flush()
        for i in range(n_records):
            ev = Event(
                id=uuid.uuid4(), title=f"Record {i}", sector="politics", regions=["IN"],
                last_updated_at=datetime.now(UTC), projection={"source_slugs": ["the_hindu"]},
            )
            s.add(ev)
            await s.flush()
            s.add(EventEntity(event_id=ev.id, entity_id=ent.id, role="subject"))
    return slug


async def _get(path: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


async def test_an_actor_with_records_is_indexable_and_lists_them_newest_first():
    if not await _db_reachable():
        pytest.skip("no database")
    slug = await _seed(INDEXABLE_MIN_RECORDS)
    r = await _get(f"/api/v1/entity/{slug}")
    assert r.status_code == 200
    body = r.json()
    assert body["entity"]["slug"] == slug
    assert body["entity"]["schema_type"] == "Person"
    assert body["record_count"] == INDEXABLE_MIN_RECORDS
    assert body["indexable"] is True
    assert len(body["records"]) == INDEXABLE_MIN_RECORDS
    times = [x["id"] for x in body["records"]]
    assert len(set(times)) == INDEXABLE_MIN_RECORDS


async def test_a_thin_actor_still_has_a_page_but_declines_indexing():
    if not await _db_reachable():
        pytest.skip("no database")
    slug = await _seed(INDEXABLE_MIN_RECORDS - 1)
    body = (await _get(f"/api/v1/entity/{slug}")).json()
    assert body["record_count"] == INDEXABLE_MIN_RECORDS - 1
    assert body["indexable"] is False, "a stub must not ask to be indexed"
    assert body["records"], "but the chip that links here must still land on something"


async def test_an_unknown_actor_is_404_not_an_empty_page():
    if not await _db_reachable():
        pytest.skip("no database")
    assert (await _get("/api/v1/entity/no-such-actor-here")).status_code == 404


async def test_the_entity_sitemap_lists_only_what_clears_the_floor():
    if not await _db_reachable():
        pytest.skip("no database")
    fat, thin = await _seed(INDEXABLE_MIN_RECORDS), await _seed(1)
    listed = {e["slug"] for e in (await _get("/api/v1/sitemap/entities")).json()["entities"]}
    assert fat in listed and thin not in listed
