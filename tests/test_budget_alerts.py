"""Founders hear about the LLM balance before readers do.

2026-09-28 02:11 UTC: the balance fell under the $5 floor, collection stopped,
and for 37 hours the only trace was a log line every five minutes. /healthz
stayed green. Readers found out first, from day-old news on every row.
"""

import pytest

from common import alerts, budget


class _Redis:
    def __init__(self):
        self.keys = {}

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.keys:
            return None
        self.keys[key] = value
        return True


class _Sender:
    def __init__(self, fail=False):
        self.sent, self.fail = [], fail

    async def send(self, *, to, subject, body, **kw):
        if self.fail:
            raise RuntimeError("resend down")
        self.sent.append((to, subject))


@pytest.fixture
def mail(monkeypatch):
    from common.config import get_settings

    r, sender = _Redis(), _Sender()
    monkeypatch.setattr(alerts, "get_redis", lambda: r)
    monkeypatch.setattr(alerts, "get_email_sender", lambda: sender)
    monkeypatch.setattr(get_settings(), "prism_admin_emails", "a@x.test, b@x.test")
    monkeypatch.setattr(get_settings(), "prism_llm_budget_floor_usd", 5.0)
    return sender


@pytest.mark.asyncio
async def test_an_alert_goes_to_every_founder_once_per_window(mail):
    assert await alerts.notify("k", "Subject", "Body") is True
    assert await alerts.notify("k", "Subject", "Body") is False
    assert mail.sent == [("a@x.test", "[Prism] Subject"), ("b@x.test", "[Prism] Subject")]


@pytest.mark.asyncio
async def test_a_failed_send_never_raises(monkeypatch, mail):
    monkeypatch.setattr(alerts, "get_email_sender", lambda: _Sender(fail=True))
    assert await alerts.notify("k2", "Subject", "Body") is False


@pytest.mark.asyncio
async def test_no_recipients_sends_nothing(monkeypatch, mail):
    from common.config import get_settings

    monkeypatch.setattr(get_settings(), "prism_admin_emails", "")
    assert await alerts.notify("k3", "Subject", "Body") is False
    assert mail.sent == []


def _ledger(*costs):
    """spend.days(): newest first, today (partial) at index 0."""
    async def days(n):
        return [{"day": f"d{i}", "recorded": c is not None, "cost": c or 0.0} for i, c in enumerate(costs)]
    return days


@pytest.mark.asyncio
async def test_stopped_collection_is_reported(monkeypatch, mail):
    monkeypatch.setattr(budget.spend, "days", _ledger(1.0, 8.0, 8.0))
    await budget.warn_if_low({"balance": 4.30, "at": 0})
    assert mail.sent and "collection has stopped" in mail.sent[0][1]


@pytest.mark.asyncio
async def test_under_two_days_of_credit_is_reported(monkeypatch, mail):
    monkeypatch.setattr(budget.spend, "days", _ledger(1.0, 8.0, 8.0))
    await budget.warn_if_low({"balance": 5.0 + 12.0, "at": 0})  # 12 over the floor at $8/day
    assert mail.sent and "days of LLM credit" in mail.sent[0][1]


@pytest.mark.asyncio
async def test_a_healthy_balance_is_quiet(monkeypatch, mail):
    monkeypatch.setattr(budget.spend, "days", _ledger(1.0, 8.0, 8.0))
    await budget.warn_if_low({"balance": 5.0 + 40.0, "at": 0})
    assert mail.sent == []


@pytest.mark.asyncio
async def test_no_ledger_is_no_runway_alarm(monkeypatch, mail):
    """Days the ledger did not record are unknown, not free."""
    monkeypatch.setattr(budget.spend, "days", _ledger(None, None, None))
    await budget.warn_if_low({"balance": 6.0, "at": 0})
    await budget.warn_if_low(None)
    assert mail.sent == []
