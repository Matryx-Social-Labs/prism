"""The QID decision rules — every case here is one that actually went wrong.

`resolve` is the whole of entity canonicalization's judgement: given the candidate
items a surface form matched, either commit to one or refuse. Getting it wrong in
the permissive direction merges two real organisations permanently, with nothing
raised anywhere, so each rule below exists because a specific real candidate set
defeated a simpler version.
"""

from tools.link_entities import is_identifying, narrow, resolve


def test_a_single_candidate_links():
    assert resolve([("Q10230", "alias")]) == ("Q10230", "alias_exact")


def test_no_candidates_is_no_link():
    assert resolve([]) is None


def test_the_same_qid_reached_by_several_forms_is_not_ambiguity():
    """A form can be both a label and an alias of one item. That is one candidate."""
    assert resolve([("Q10230", "label"), ("Q10230", "alias")]) == ("Q10230", "alias_exact")


def test_a_label_beats_another_items_alias():
    """The CPI case, verbatim. Q234277 is the CPI(Marxist) and lists plain
    "Communist Party of India" as an alias; Q837159 IS the Communist Party of
    India and carries that string as its label. Merging them is a wrong fold of
    two real, separately-active parties."""
    assert resolve([("Q234277", "alias"), ("Q837159", "label")]) == ("Q837159", "label_wins")


def test_a_wiki_title_beats_an_alias_but_loses_to_a_label():
    assert resolve([("Q1", "sitelink"), ("Q2", "alias")]) == ("Q1", "sitelink_wins")
    assert resolve([("Q1", "sitelink"), ("Q2", "label")]) == ("Q2", "label_wins")


def test_two_candidates_at_the_same_tier_are_refused_not_ranked():
    """Indian National Congress matches both the current party and a 1969-77
    splinter, both carrying that exact label. Aam Aadmi Party matches an Indian
    and a Pakistani party. Name alone cannot separate these, so nothing may."""
    assert resolve([("Q10225", "label"), ("Q3523002", "label")]) is None
    assert resolve([("Q129844", "label"), ("Q17003198", "label")]) is None


def test_ambiguity_is_refused_at_the_weakest_tier_too():
    assert resolve([("Q234277", "alias"), ("Q837159", "alias")]) is None


def test_prominence_is_never_available_to_break_a_tie():
    """The rule that got this wrong once. `resolve` is not GIVEN a prominence
    signal at all — it takes only (qid, kind) — so a future edit cannot quietly
    reintroduce the tie-break that merged the CPI into the CPI(Marxist) on 52
    sitelinks against 46. Asserting the signature is what makes that structural
    rather than a convention someone can drift away from."""
    import inspect

    assert list(inspect.signature(resolve).parameters) == ["cands"], (
        "resolve gained an input; prominence must not be one"
    )


def test_an_unknown_kind_is_treated_as_the_weakest():
    """A kind we do not recognise must never outrank a real label. Defaulting the
    other way would let a future column value silently win every tie."""
    assert resolve([("Q1", "label"), ("Q2", "something-new")]) == ("Q1", "label_wins")


# --- context narrowing: convert refusals into links, never links into other links ---
# `narrow` runs BEFORE `resolve`, so `resolve` keeps taking nothing but (qid, kind)
# and the prominence signal that once merged two parties stays out of reach.

LIVE = {"defunct": False, "countries": {"Q668"}}
DEAD = {"defunct": True, "countries": {"Q668"}}
PAKISTANI = {"defunct": False, "countries": {"Q843"}}


def test_a_defunct_candidate_loses_to_a_live_one():
    """Indian National Congress matches the sitting party and a splinter that
    existed 1969-77, with identical labels. Nothing in the name separates them."""
    cands = [("Q10225", "label"), ("Q3523002", "label")]
    got, applied = narrow(cands, {"Q10225": LIVE, "Q3523002": DEAD})
    assert got == [("Q10225", "label")]
    assert applied == ["live"]
    assert resolve(got) == ("Q10225", "alias_exact")


def test_all_defunct_narrows_to_nothing_and_stays_refused():
    """Never empty the set. A historical story about two dissolved organisations
    is still ambiguous, and inventing a winner would be worse than refusing."""
    cands = [("Q1", "label"), ("Q2", "label")]
    got, applied = narrow(cands, {"Q1": DEAD, "Q2": DEAD})
    assert got == cands and applied == []
    assert resolve(got) is None


def test_country_breaks_a_tie_only_after_liveness_fails():
    """Aam Aadmi Party matches an Indian and a Pakistani party, both live."""
    cands = [("Q129844", "label"), ("Q17003198", "label")]
    got, applied = narrow(cands, {"Q129844": LIVE, "Q17003198": PAKISTANI})
    assert got == [("Q129844", "label")] and applied == ["india"]


def test_country_is_not_applied_when_liveness_already_decided():
    """Ordering matters: a live non-Indian candidate must not then be dropped for
    being foreign when liveness had already produced a single answer."""
    _, applied = narrow(
        [("Q1", "label"), ("Q2", "label")], {"Q1": PAKISTANI, "Q2": DEAD}
    )
    assert applied == ["live"], "country narrowed a set that liveness had settled"


def test_two_live_indian_candidates_stay_refused():
    """Three different people named Amit Shah. Neither signal separates them, and
    neither should pretend to."""
    cands = [("Q1", "label"), ("Q2", "label")]
    got, applied = narrow(cands, {"Q1": LIVE, "Q2": LIVE})
    assert got == cands and applied == []
    assert resolve(got) is None


def test_missing_context_changes_nothing():
    """When the context lookup fails the dict is empty. That must cost recall, not
    precision — every ambiguous name stays refused, exactly as before."""
    cands = [("Q1", "label"), ("Q2", "label")]
    assert narrow(cands, {}) == (cands, [])


def test_narrow_never_adds_a_candidate():
    cands = [("Q1", "label"), ("Q2", "label"), ("Q3", "alias")]
    got, _ = narrow(cands, {"Q1": LIVE, "Q2": DEAD, "Q3": DEAD})
    assert set(got) <= set(cands)


# --- weak aliases: where the false merges actually came from ---------------------
# A single-token ALIAS is the weakest evidence Wikidata offers. Q114270322 is a
# Kashmiri poet whose item lists BOTH "Rahul" and "Kiran" as aliases, so two
# unrelated people in the corpus were folded into a poet neither of them is.
# But single-token aliases are also the most valuable folds (bjp, cbi, rss), so the
# test is not "reject short" — it is "reject what the item's own name cannot yield".


def test_an_initialism_of_the_item_name_is_identifying():
    assert is_identifying("bjp", "alias", ["Bharatiya Janata Party"])
    assert is_identifying("cbi", "alias", ["Central Bureau of Investigation"])


def test_joining_words_are_skipped_when_forming_the_initialism():
    """Press Trust of India is PTI, not PTOI."""
    assert is_identifying("pti", "alias", ["Press Trust of India"])


def test_a_word_of_the_name_is_identifying():
    """Shortened personal names: 'Vijay' for C. Joseph Vijay."""
    assert is_identifying("vijay", "alias", ["C. Joseph Vijay"])
    assert is_identifying("kanimozhi", "alias", ["Kanimozhi Karunanidhi"])


def test_a_bare_name_unrelated_to_the_item_is_refused():
    """The actual production defect: both of these were aliases on ONE poet's item
    and merged two unrelated people."""
    assert not is_identifying("rahul", "alias", ["Hemangi Sharma"])
    assert not is_identifying("kiran", "alias", ["Hemangi Sharma"])


def test_labels_and_wiki_titles_are_exempt():
    """Those ARE the item's name, so 'is it derived from the name' cannot apply —
    and requiring it would reject every single-word label, e.g. Infosys."""
    assert is_identifying("anything", "label", [])
    assert is_identifying("anything", "sitelink", [])


def test_a_multi_token_alias_is_specific_enough_on_its_own():
    assert is_identifying("press-trust-of-india", "alias", [])


def test_an_item_with_no_recorded_label_cannot_vouch_for_a_bare_alias():
    """No labels means no evidence the alias derives from the name. Refuse rather
    than default to trusting it — absence of evidence must not permit an action."""
    assert not is_identifying("rahul", "alias", [])
