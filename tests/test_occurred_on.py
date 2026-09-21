"""The extracted `occurred_at` can name a day the article is ABOUT ("rules change
from October 1"), which is not a day the event happened. Such a date is dropped;
the readers of the column fall back to when the story was first seen."""

from datetime import UTC, date, datetime

from enrichment.consumer import occurred_on

PUB = datetime(2026, 9, 16, 10, 0, tzinfo=UTC)  # 15:30 IST on the 16th


def test_a_date_after_the_report_is_not_when_it_happened():
    assert occurred_on("2026-10-01", PUB) is None
    assert occurred_on("2028-01-01T00:00:00", PUB) is None


def test_the_report_day_and_the_days_before_it_stand_and_tomorrow_does_not():
    assert occurred_on("2026-09-16", PUB) == date(2026, 9, 16)
    assert occurred_on("2026-09-15", PUB) == date(2026, 9, 15)
    # "Launching tomorrow" is not a thing that happened.
    assert occurred_on("2026-09-17", PUB) is None


def test_the_report_day_is_read_on_the_indian_clock():
    # 20:30 UTC on the 16th is 02:00 IST on the 17th: the article says the 17th.
    late = datetime(2026, 9, 16, 20, 30, tzinfo=UTC)
    assert occurred_on("2026-09-17", late) == date(2026, 9, 17)
    assert occurred_on("2026-09-18", late) is None


def test_nothing_to_clamp_against_leaves_the_date_alone():
    assert occurred_on("2026-10-01", None) == date(2026, 10, 1)
    assert occurred_on(None, PUB) is None
    assert occurred_on("not a date", PUB) is None
    assert occurred_on("2026-09-16", date(2026, 9, 16)) == date(2026, 9, 16)
