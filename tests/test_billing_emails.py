"""The three emails a subscription owes: welcome, payment failed, cancelled — and none for noise."""

import uuid

import pytest
from sqlalchemy import text

import common.billing_emails as be
from common.db import session_scope

pytestmark = pytest.mark.asyncio(loop_scope="session")


class _Sender:
    def __init__(self):
        self.sent = []

    async def send(self, *, to, subject, body, html=None):
        self.sent.append((to, subject, body, html))


async def _db() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def test_each_transition_sends_its_email_and_others_send_nothing(monkeypatch):
    if not await _db():
        pytest.skip("no local database")
    sender = _Sender()
    monkeypatch.setattr(be, "get_email_sender", lambda: sender)
    email = f"billing-mail-{uuid.uuid4().hex[:8]}@t.test"
    async with session_scope() as s:
        uid = (await s.execute(text("INSERT INTO users (id, email) VALUES (gen_random_uuid(), :e) RETURNING id"), {"e": email})).scalar_one()
    sub = {"id": "sub_x", "status": "active", "current_end": 4102444800, "notes": {"plan": "plus_yearly"}}
    try:
        async with session_scope() as s:
            await be.notify_transition(s, str(uid), "created", "active", sub)
            await be.notify_transition(s, str(uid), "active", "past_due", {**sub, "status": "pending"})
            await be.notify_transition(s, str(uid), "active", "cancelled", {**sub, "status": "cancelled"})
            await be.notify_transition(s, str(uid), "active", "active", sub)  # a re-sync: nothing owed
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM users WHERE id = :u"), {"u": str(uid)})
    subjects = [x[1] for x in sender.sent]
    assert subjects == ["You're on Prism Plus", "A Prism Plus charge did not go through", "Your Prism Plus has been cancelled"]
    welcome = sender.sent[0]
    assert welcome[0] == email and "Plus · yearly" in welcome[2] and "1 January 2100" in welcome[2]
    assert "/account" in welcome[3] and "<h1" in welcome[3]
