"""How a practice or qualification answer is marked, and what makes a test fair.

One rule for every task kind, because every kind stores its answer the same way
(api/routes/label.py): `selected` is a set of ids — candidate events that are the
same story or happening, or the task's own id as the sentinel for "yes, the
article credits these words to this person" — plus `unsure` and `skipped`.

    correct  <=>  not unsure, not skipped, and set(selected) == set(expected)

Unsure and skip are real answers on WORK (label.py keeps them apart on purpose),
but a test item is drawn only from answers the founders AGREED on, so it has an
answer and "not sure" is a miss. That is also the only way a test can be passed
by reading the guide rather than by declining to decide.

A TEST THAT A CONSTANT STRATEGY CAN PASS IS NOT A TEST. The adjudicated gold sets
are lopsided — claims are 58 yes to 1 no, story pairs 42 positive in 1,147 — so a
draw from them unbalanced would pass anyone who always answers "yes" or never
ticks anything. `constant_strategy_scores` measures what the lazy strategies
would score on a pool; tools/label_qualify refuses to publish a pool where any of
them reaches the pass mark.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

# Founder decision 2026-09-23: 90% on every qualification test.
PASS_MARK = 0.90
# Items drawn per attempt from a kind's qualification pool.
QUESTIONS_PER_TEST = 15
# A failed attempt can be retaken after this long, on a fresh random draw.
RETAKE_AFTER_HOURS = 24


def is_correct(answer: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    if answer.get("unsure") or answer.get("skipped"):
        return False
    return {str(x) for x in answer.get("selected") or []} == {str(x) for x in expected.get("selected") or []}


def score(pairs: Iterable[tuple[Mapping[str, Any], Mapping[str, Any]]]) -> tuple[int, int]:
    """(right, total) over (answer, expected) pairs."""
    right = total = 0
    for answer, expected in pairs:
        total += 1
        right += is_correct(answer, expected)
    return right, total


def constant_strategy_scores(items: list[dict[str, Any]]) -> dict[str, float]:
    """What someone who does not read would score on this pool.

    `items` are tasks as the builder holds them: `expected`, and for event-shaped
    tasks the `candidates` they could tick. "Tick nothing", "tick everything"
    and, for claim tasks, "always yes" are the strategies that need no reading.
    """
    if not items:
        return {}
    strategies = {
        "tick nothing / always no": lambda it: [],
        "tick everything / always yes": lambda it: (
            [c["id"] for c in it.get("candidates") or []] or [it["id"]]
        ),
    }
    out = {}
    for name, pick in strategies.items():
        right, total = score(({"selected": pick(it)}, it["expected"]) for it in items)
        out[name] = right / total
    return out


def demo() -> None:
    """Self-check: the marking rule, and that the fairness check catches a lopsided pool."""
    assert is_correct({"selected": ["b", "a"]}, {"selected": ["a", "b"]})
    assert not is_correct({"selected": ["a"]}, {"selected": ["a", "b"]})
    assert not is_correct({"selected": ["a"], "unsure": True}, {"selected": ["a"]}), "unsure is a miss on a test"
    assert not is_correct({"selected": [], "skipped": True}, {"selected": []}), "a skip is a miss on a test"
    assert is_correct({"selected": []}, {"selected": []}), "tick nothing is right when nothing matches"
    assert score([({"selected": ["x"]}, {"selected": ["x"]}), ({"selected": []}, {"selected": ["y"]})]) == (1, 2)

    lopsided = [{"id": f"t{i}", "expected": {"selected": [f"t{i}"]}} for i in range(19)] + [
        {"id": "t19", "expected": {"selected": []}}]
    assert constant_strategy_scores(lopsided)["tick everything / always yes"] >= PASS_MARK, \
        "a 19-yes-1-no claim pool IS passable by always saying yes — the check must see it"
    balanced = [{"id": f"y{i}", "expected": {"selected": [f"y{i}"]}} for i in range(8)] + [
        {"id": f"n{i}", "expected": {"selected": []}} for i in range(7)]
    assert max(constant_strategy_scores(balanced).values()) < PASS_MARK
    print(f"ok: marking rule, constant strategies caught (pass mark {PASS_MARK})")


if __name__ == "__main__":
    demo()
