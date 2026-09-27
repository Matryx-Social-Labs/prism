"""The lens registry promises only what the record holds (audit, 2026-09-27).

/api/v1/lenses serves these words to every picker. The Reader lens promised
"both sides" (retired with the stance labels, D4) and Markets promised
"price-impact reads" while Prism holds no price data at all.
"""

from common.lenses import active_lenses


def test_no_served_lens_promises_sides_or_prices():
    copy = " ".join(" ".join([lens.tagline, *lens.suggested_questions]) for lens in active_lenses()).lower()
    assert "side" not in copy, "a both-sides promise (retired, D4)"
    assert "price" not in copy, "a price promise, and there is no price data"
