"""The emails a subscription owes: welcome, charge failed, cancel scheduled,
will-not-renew / ended, refunded — and none for noise or on top of a refund."""

import uuid
from datetime import UTC, datetime, timedelta

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


async def _user() -> tuple[str, str]:
    email = f"billing-mail-{uuid.uuid4().hex[:8]}@t.test"
    async with session_scope() as s:
        uid = (await s.execute(text("INSERT INTO users (id, email) VALUES (gen_random_uuid(), :e) RETURNING id"), {"e": email})).scalar_one()
    return str(uid), email


async def _drop(uid: str):
    async with session_scope() as s:
        await s.execute(text("DELETE FROM users WHERE id = :u"), {"u": uid})


async def test_each_transition_sends_its_email_and_others_send_nothing(monkeypatch):
    if not await _db():
        pytest.skip("no local database")
    sender = _Sender()
    monkeypatch.setattr(be, "get_email_sender", lambda: sender)
    uid, email = await _user()
    sub = {"id": "sub_x", "status": "active", "current_end": 4102444800, "current_start": 4070908800, "notes": {"plan": "plus_yearly", "price_paise": "149900"}}
    try:
        async with session_scope() as s:
            await be.notify_transition(s, uid, "created", "active", sub)
            await be.notify_transition(s, uid, "active", "past_due", {**sub, "status": "pending"})
            # Razorpay-side cancel (mandate revoked) with the period still running: will not renew.
            await be.notify_transition(s, uid, "active", "cancelled", {**sub, "status": "cancelled"})
            # The same, but the period is over: ended.
            await be.notify_transition(s, uid, "active", "cancelled", {**sub, "status": "cancelled", "current_end": 946684800})
            await be.notify_transition(s, uid, "active", "halted", {**sub, "status": "halted"})
            await be.notify_transition(s, uid, "active", "active", sub)  # a re-sync: nothing owed
            await be.notify_transition(s, uid, "created", "expired", {**sub, "status": "expired"})  # never paid: nothing owed
    finally:
        await _drop(uid)
    subjects = [x[1] for x in sender.sent]
    assert subjects == [
        "You're on Prism Plus",
        "A Prism Plus charge did not go through",
        "Your Prism Plus will not renew",
        "Your Prism Plus has ended",
        "Prism Plus is paused",
    ]
    welcome = sender.sent[0]
    assert welcome[0] == email and "Plus · yearly" in welcome[2] and "1 January 2100" in welcome[2] and "₹1,499" in welcome[2]
    assert "/account" in welcome[3] and "<h1" in welcome[3] and "Next charge" in welcome[3]
    not_renew = sender.sent[2][2]
    assert "You keep Plus until 1 January 2100" in not_renew
    ended = sender.sent[3][2]
    assert "ended on 1 January 2000" in ended and "No further charges" in ended


async def test_billing_dates_are_the_indian_calendar_day_razorpay_bills_on(monkeypatch):
    """The founder paid from Berlin at 20:50 on 20 Sept; Razorpay charged at 00:20
    IST on the 21st and ends the cycle at 00:00 IST on 21 Sept 2027. The UTC date
    of that instant is the 20th; the receipt says the 21st; so do we."""
    if not await _db():
        pytest.skip("no local database")
    sender = _Sender()
    monkeypatch.setattr(be, "get_email_sender", lambda: sender)
    uid, _ = await _user()
    try:
        async with session_scope() as s:
            await be.notify_transition(s, uid, "created", "active", {"id": "sub_tz", "status": "active", "current_start": 1789930228, "current_end": 1821465000, "notes": {"plan": "plus_yearly", "price_paise": "119900"}})
    finally:
        await _drop(uid)
    body = sender.sent[0][2]
    assert "Next charge: 21 September 2027 IST" in body
    assert "20 September 2027" not in body


async def test_a_scheduled_cancel_is_confirmed_at_once_and_its_end_is_reported_as_ended(monkeypatch):
    """The reader clicks Cancel: one email now with the date. When Razorpay
    later reports the cancellation at cycle end, the reader is told it ENDED —
    never 'you keep Plus until' a date that has passed."""
    if not await _db():
        pytest.skip("no local database")
    sender = _Sender()
    monkeypatch.setattr(be, "get_email_sender", lambda: sender)
    uid, email = await _user()
    until = datetime(2027, 3, 1, tzinfo=UTC)
    try:
        async with session_scope() as s:
            await s.execute(
                text(
                    "INSERT INTO subscriptions (id, user_id, provider, provider_sub_id, plan, status, current_period_end, cancel_at, price_paise) "
                    "VALUES (gen_random_uuid(), :u, 'razorpay', 'sub_sched', 'plus_monthly', 'active', :end, :end, 14900)"
                ),
                {"u": uid, "end": until},
            )
            await be.notify_cancel_scheduled(s, uid, plan_key="plus_monthly", price_paise=14900, access_until=until)
            # Cycle end arrives; Razorpay's entity still says current_end = that (now past) date.
            await be.notify_transition(s, uid, "active", "cancelled", {"id": "sub_sched", "status": "cancelled", "current_end": int(until.timestamp()), "notes": {"plan": "plus_monthly"}})
    finally:
        await _drop(uid)
    assert [x[1] for x in sender.sent] == ["Your Prism Plus is set to end", "Your Prism Plus has ended"]
    first = sender.sent[0]
    assert first[0] == email and "1 March 2027" in first[2] and "Plus ends" in first[3] and "None" in first[3]
    assert "will not renew" not in sender.sent[1][1]


async def test_the_refund_email_says_the_amount_the_reference_and_when_and_nothing_follows_it(monkeypatch):
    if not await _db():
        pytest.skip("no local database")
    sender = _Sender()
    monkeypatch.setattr(be, "get_email_sender", lambda: sender)
    uid, email = await _user()
    now = datetime.now(UTC)
    try:
        async with session_scope() as s:
            await s.execute(
                text(
                    "INSERT INTO subscriptions (id, user_id, provider, provider_sub_id, plan, status, current_period_end, cancel_at, price_paise, refund_id) "
                    "VALUES (gen_random_uuid(), :u, 'razorpay', 'sub_rf', 'plus_yearly', 'cancelled', :now, :now, 149900, 'rfnd_1')"
                ),
                {"u": uid, "now": now},
            )
            await be.notify_refund(s, uid, plan_key="plus_yearly", amount_paise=149900, refund_id="rfnd_1", ended=now)
            # The cancel webhook that follows the refund owes nothing more.
            await be.notify_transition(s, uid, "active", "cancelled", {"id": "sub_rf", "status": "cancelled", "current_end": int((now + timedelta(days=300)).timestamp()), "notes": {"plan": "plus_yearly"}})
    finally:
        await _drop(uid)
    assert [x[1] for x in sender.sent] == ["Refunded: ₹1,499 for Prism Plus"]
    _, _, body, html = sender.sent[0]
    assert "rfnd_1" in body and "5–7 working days" in body and "₹1,499" in html and "/feed" in html
