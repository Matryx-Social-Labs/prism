"""Placing a story on the subject tree, in one extra question per level.

The tree asks a different question at each level with the parent fixed, because
that is the shape a decision model answers best: seven siblings, then six, then
four, each menu short enough to be read carefully. A flat 54-way question is
the same information and a worse answer — and it is exactly how
`business/corporate` came to hold a dairy building.

THE COST OF DEPTH IS ALMOST NOTHING, because Jev answers every question in one
parallel pass. The root and ALL the level-2 menus ride in the call that already
gates and classifies the item: the level-2 answers for branches we did not take
are simply discarded. Only the two branches that go three deep
(`tech.security`, `civic.crime`) need a second call, and only when the story
lands there — about one item in eight.

A PARENT IS A VALID RESTING PLACE (founder, 2026-09-22). Every child menu
carries an explicit `general` option, so a crime story that does not say
whether it was violence or theft stops at `civic.crime` rather than being
forced into a leaf it does not belong in. A wrong leaf is worse than an honest
branch: the leaf is a claim about the story, the branch is what we know.
"""

from __future__ import annotations

from common import subjects
from common.decisions import Choice, ChoiceAnswer, Decisions, Question

# The option that means "this branch, but none of its children". Not a node:
# choosing it resolves to the parent's own path.
STAY = "general"
STAY_CRITERION = "this subject in general, or the story does not say which of the others it is"

# Under this, the model is not sure enough to go deeper and the path stops at
# the parent. Measured per branch before it ships — see tools/bakeoff_subject.
DESCEND_MIN_CONFIDENCE = 0.55


def _menu(parent: str | None) -> dict[str, str]:
    """The children of a node as a decision menu, plus the way to stay put."""
    options = subjects.choices(parent)
    if parent is not None:
        options[STAY] = STAY_CRITERION
    return options


def root_question() -> Question:
    return Choice(
        instructions="The subject the story belongs to. Choose by what the story is ABOUT, not by who is in it or where it happened",
        criteria=_menu(None),
    )


def level_two_questions() -> dict[str, Question]:
    """One question per root, keyed `sub_<root>`. They all ride in the same
    call; only the chosen root's answer is read."""
    return {
        f"sub_{root}": Choice(
            instructions=f"If the story is about {subjects.get(root).label.lower()}, which part of it",
            criteria=_menu(root),
        )
        for root in subjects.ROOTS
    }


def level_three_question(parent: str) -> dict[str, Question]:
    """The second call, for the two branches that go deeper."""
    return {
        "leaf": Choice(
            instructions=f"Within {subjects.get(parent).label.lower()}, which kind",
            criteria=_menu(parent),
        )
    }


def needs_third_level(path: str) -> bool:
    return bool(subjects.children(path))


def path_from(answers: Decisions) -> tuple[str | None, float]:
    """The path and the confidence it was placed with, from one call's answers.

    Descends only while the model is sure: an unsure level-2 answer leaves the
    story on its root, which is a true statement about a story we could not
    place, rather than a false one about a story we could.

    No answer, or an answer off the menu, gives NO path rather than a guessed
    one. An unplaced story is visible and fixable; a story filed under the
    wrong root is neither."""
    root = answers.answers.get("subject")
    if root is None or not isinstance(root, ChoiceAnswer):
        return None, 0.0
    path, confidence = root.choice, root.confidence
    if not subjects.is_valid(path):
        return None, confidence
    child = answers.answers.get(f"sub_{path}")
    if child is None or child.choice == STAY or child.confidence < DESCEND_MIN_CONFIDENCE:
        return path, confidence
    candidate = f"{path}.{child.choice}"
    if not subjects.is_valid(candidate):
        return path, confidence
    return candidate, min(confidence, child.confidence)


def deepen(path: str, answers: Decisions) -> tuple[str, float]:
    """Apply the second call's answer, if it earned one."""
    leaf = answers.answers.get("leaf")
    if leaf is None or leaf.choice == STAY or leaf.confidence < DESCEND_MIN_CONFIDENCE:
        return path, leaf.confidence if leaf else 1.0
    candidate = f"{path}.{leaf.choice}"
    return (candidate, leaf.confidence) if subjects.is_valid(candidate) else (path, leaf.confidence)


def demo() -> None:
    """Self-check: every menu is short, every option resolves, `general` never
    collides with a real node, and a leaf question exists where the tree goes
    three deep."""
    root_opts = _menu(None)
    assert set(root_opts) == set(subjects.ROOTS)
    assert STAY not in root_opts, "the root has no parent to stay at"
    for root in subjects.ROOTS:
        menu = _menu(root)
        assert STAY in menu
        assert len(menu) <= 10, f"{root} menu is too long to read carefully: {len(menu)}"
        for slug in menu:
            if slug == STAY:
                continue
            assert subjects.is_valid(f"{root}.{slug}"), f"{root}.{slug} is not a node"
    deep = [s.path for s in subjects.SUBJECTS if subjects.children(s.path) and subjects.depth(s.path) == 2]
    assert set(deep) == {"tech.security", "civic.crime"}, deep
    for parent in deep:
        assert "leaf" in level_three_question(parent)
    assert len(level_two_questions()) == len(subjects.ROOTS)
    print(f"ok: 1 root menu of {len(root_opts)}, {len(subjects.ROOTS)} level-2 menus, {len(deep)} branches that go deeper")


if __name__ == "__main__":
    demo()
