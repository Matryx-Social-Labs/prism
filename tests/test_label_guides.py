"""The labelling guides: who is sent them, and what they must say.

Founder, 2026-09-23: "do not leak this to outsiders". The guides left the
site's public JavaScript for common/label_guides.py; these tests pin that the
API sends them only to an account that has applied (G1) and to a batch's own
invite — and the content rules the web tests used to pin, now that the words
live here.
"""

import json
import re
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from common import auth
from common.db import session_scope
from common.label_guides import GUIDES, KINDS

pytestmark = pytest.mark.asyncio(loop_scope="session")
WEB = Path(__file__).resolve().parent.parent / "web"


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


def _all_text(g: dict) -> str:
    return json.dumps(g, ensure_ascii=False)


# ── what the guides say ──────────────────────────────────────────────────────

async def test_every_kind_the_web_teaches_has_a_guide_and_every_guide_is_whole():
    learnable = re.search(r"LEARNABLE[^=]*=\s*\[([^\]]*)\]", (WEB / "src/lib/labeller.ts").read_text())
    assert learnable, "web/src/lib/labeller.ts LEARNABLE moved"
    assert set(re.findall(r'"(\w+)"', learnable.group(1))) == set(KINDS)
    for kind, g in GUIDES.items():
        assert g["question"] and g["in_short"] and g["lede"] and g["start"], kind
        for ex in g["examples"]:
            assert ex.get("mark") in (None, "yes", "no"), (kind, ex["head"])
            # The Legend Rule: the verdict is a word in the head, never the icon alone.
            assert re.match(r"^[A-Z][A-Z ]+ —", ex["head"]), (kind, ex["head"])


async def test_a_late_report_is_the_same_happening():
    """Founder correction, 2026-09-23 (phase A): the same incident, whatever day
    it was reported. 252 of 364 cross-language candidates are dated after their seed."""
    g = GUIDES["event_identity"]
    words = _all_text(g)
    assert "When it was reported does not matter" in words
    assert "late report" in words
    assert not re.search(r"same day|a day apart", words, re.IGNORECASE)
    invented = [ex for ex in g["examples"] if ex.get("illustration")]
    assert len(invented) == 1 and "late report" in invented[0]["body"]


async def test_the_story_guide_teaches_both_mistakes_that_were_made():
    """Over-ticking (round 1: a shared word, a shared organisation) and
    under-ticking (round 2: one incident, many outlets, two languages). Teaching
    only one is how the fix to one became the cause of the other."""
    words = _all_text(GUIDES["story_boundary"])
    assert "Monsoon Session" in words and "shared organisation" in words
    assert "one breach reported twice" in words
    assert "two languages" in words and "five reports of one" in words


async def test_each_guide_keeps_to_its_own_question():
    # Story guidance must not leak into the claim guide; they ask opposite things.
    assert "Monsoon" not in _all_text(GUIDES["claim_attribution"])
    assert "right quote, wrong mouth" in _all_text(GUIDES["claim_attribution"]).lower()
    topic = _all_text(GUIDES["topic_relation"])
    assert "different stories" in topic and "same unfolding story" not in topic


# ── who is sent them ─────────────────────────────────────────────────────────

async def _account(status: str | None) -> tuple[uuid.UUID, str]:
    uid = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(text("INSERT INTO users (id, email) VALUES (:i, :e)"), {"i": uid, "e": f"g-{uid.hex[:10]}@example.test"})
        if status:
            await s.execute(text("INSERT INTO labellers (user_id, languages_read, status) VALUES (:u, ARRAY['en'], :s)"),
                            {"u": uid, "s": status})
        bearer = await auth.create_session(s, uid)
    return uid, bearer


async def _drop(*uids: uuid.UUID) -> None:
    async with session_scope() as s:
        for uid in uids:
            await s.execute(text("DELETE FROM label_invites WHERE user_id = :u"), {"u": uid})
            await s.execute(text("DELETE FROM sessions WHERE user_id = :u"), {"u": uid})
            await s.execute(text("DELETE FROM users WHERE id = :u"), {"u": uid})


async def test_only_someone_who_has_applied_is_sent_a_guide():
    if not await _db_reachable():
        pytest.skip("no database")
    people = {status: await _account(status) for status in (None, "applied", "active", "paused", "removed")}
    try:
        async with _client() as c:
            assert (await c.get("/api/v1/labeller/guides/event_identity")).status_code == 401
            got = {}
            for status, (_, bearer) in people.items():
                r = await c.get("/api/v1/labeller/guides/event_identity", headers={"Authorization": f"Bearer {bearer}"})
                got[status] = r.status_code
                if r.status_code == 200:
                    assert r.json()["question"] == "Is this the same happening?"
                else:
                    assert "same incident" not in r.text
            assert got == {None: 403, "applied": 200, "active": 200, "paused": 200, "removed": 403}
            _, bearer = people["active"]
            r = await c.get("/api/v1/labeller/guides/made_up", headers={"Authorization": f"Bearer {bearer}"})
            assert r.status_code == 404
    finally:
        await _drop(*(uid for uid, _ in people.values()))


async def test_a_batch_invite_is_sent_its_own_kinds_guide_and_nothing_else_is():
    if not await _db_reachable():
        pytest.skip("no database")
    keys, invites = [], {}
    paused, _ = await _account("paused")
    try:
        async with session_scope() as s:
            for kind in ("claim_attribution", "event_identity"):
                bid, key = uuid.uuid4(), f"g{uuid.uuid4().hex[:12]}"
                await s.execute(text("INSERT INTO label_batches (id, key, name, kind) VALUES (:i, :k, 'g', :kind)"),
                                {"i": bid, "k": key, "kind": kind})
                keys.append(key)
                anon, own = uuid.uuid4().hex, uuid.uuid4().hex
                await s.execute(text("INSERT INTO label_invites (id, token, batch_id) VALUES (:i, :t, :b)"),
                                {"i": uuid.uuid4(), "t": anon, "b": bid})
                await s.execute(text("INSERT INTO label_invites (id, token, batch_id, user_id) VALUES (:i, :t, :b, :u)"),
                                {"i": uuid.uuid4(), "t": own, "b": bid, "u": paused})
                invites[kind] = (key, anon, own)
        claim_key, claim_anon, claim_paused = invites["claim_attribution"]
        _, event_anon, _ = invites["event_identity"]
        async with _client() as c:
            def get(key: str, token: str | None):
                return c.get(f"/api/v1/label/{key}/guide", headers={"X-Label-Token": token} if token else {})
            # A founder's link (an anonymous invite) reads its batch's guide.
            r = await get(claim_key, claim_anon)
            assert r.status_code == 200 and r.json()["kind"] == "claim_attribution"
            # No credential, a credential for ANOTHER batch, or a paused account's: nothing.
            assert (await get(claim_key, None)).status_code == 403
            assert (await get(claim_key, event_anon)).status_code == 403
            assert (await get(claim_key, claim_paused)).status_code == 403
            assert (await get("nokey", claim_anon)).status_code == 404
    finally:
        async with session_scope() as s:
            for key in keys:
                await s.execute(text("DELETE FROM label_invites WHERE batch_id = (SELECT id FROM label_batches WHERE key = :k)"), {"k": key})
                await s.execute(text("DELETE FROM label_batches WHERE key = :k"), {"k": key})
        await _drop(paused)
