"""Ingestion stops collecting under the LLM budget floor — and only on evidence."""

from common import budget


def test_below_floor_needs_a_recorded_balance(monkeypatch):
    from common.config import get_settings

    monkeypatch.setattr(get_settings(), "prism_llm_budget_floor_usd", 5.0)
    assert budget.below_floor(None) is False  # never read: no evidence, no action
    assert budget.below_floor({"balance": 4.99, "at": 0}) is True
    assert budget.below_floor({"balance": 5.0, "at": 0}) is False


def test_a_floor_of_zero_disables_the_gate(monkeypatch):
    from common.config import get_settings

    monkeypatch.setattr(get_settings(), "prism_llm_budget_floor_usd", 0.0)
    assert budget.below_floor({"balance": -1.0, "at": 0}) is False
