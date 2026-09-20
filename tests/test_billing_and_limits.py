"""Entitlement, the offer, and the Ask brakes — the pure parts."""
from datetime import UTC, datetime, timedelta

from common.billing import entitled
from common.quota import ANON_ASK_PER_SESSION, PLUS_ASK_PER_DAY, USER_ASK_PER_DAY


def test_plus_stays_on_through_the_grace_after_a_failed_charge():
    now = datetime(2026, 9, 20, tzinfo=UTC)
    assert entitled("active", now + timedelta(days=20), now)
    assert entitled("past_due", now - timedelta(days=2), now), "two days into dunning: still on"
    assert not entitled("past_due", now - timedelta(days=4), now), "past the grace: off"
    assert not entitled("cancelled", now + timedelta(days=20), now)
    assert entitled("active", None, now), "a manual grant with no period end is on"


def test_the_caps_are_ordered_as_the_business_model_says():
    assert ANON_ASK_PER_SESSION < USER_ASK_PER_DAY < PLUS_ASK_PER_DAY
    assert (ANON_ASK_PER_SESSION, USER_ASK_PER_DAY, PLUS_ASK_PER_DAY) == (3, 10, 100)
