"""The QID decision rules — every case here is one that actually went wrong.

`resolve` is the whole of entity canonicalization's judgement: given the candidate
items a surface form matched, either commit to one or refuse. Getting it wrong in
the permissive direction merges two real organisations permanently, with nothing
raised anywhere, so each rule below exists because a specific real candidate set
defeated a simpler version.
"""

from tools.link_entities import fold_groups, is_identifying, narrow, resolve


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


# --- grouping: QID or the same name respaced, but never across a QID conflict ----


def _e(eid, slug, df=2):
    return {"id": eid, "slug": slug, "name": slug, "df": df}


def test_entities_sharing_a_qid_group():
    ents = [_e(1, "bjp"), _e(2, "bharatiya-janata-party")]
    linked = {1: ("Q10230", "alias_exact"), 2: ("Q10230", "alias_exact")}
    assert len(fold_groups(ents, linked)) == 1


def test_separator_only_differences_group_without_wikidata():
    """Wikidata does not record every variant: "Brijbhushan Sharan Singh" is not an
    alias of Q4967969 even though "Brij Bhushan Sharan Singh" is its label. Removing
    separators is what catches those, and it asks Wikidata nothing."""
    ents = [_e(1, "brij-bhushan-sharan-singh"), _e(2, "brijbhushan-sharan-singh")]
    assert len(fold_groups(ents, {1: ("Q4967969", "alias_exact")})) == 1


def test_a_qid_conflict_refuses_the_fold_even_when_slugs_match():
    """Production case: thawar-chand-gehlot is Q7711496, thawarchand-gehlot is
    Q107433711. Almost certainly duplicate items for one person — but Wikidata
    saying "distinct" outranks a missing space, and de-duplicating Wikidata is not
    this fold's job."""
    ents = [_e(1, "thawar-chand-gehlot"), _e(2, "thawarchand-gehlot")]
    linked = {1: ("Q7711496", "alias_exact"), 2: ("Q107433711", "alias_exact")}
    assert fold_groups(ents, linked) == []


def test_unrelated_entities_do_not_group():
    assert fold_groups([_e(1, "narendra-modi"), _e(2, "rahul-gandhi")], {}) == []


def test_grouping_is_transitive_across_both_keys():
    """A shares a QID with B; B is the same name as C respaced. All three are one."""
    ents = [_e(1, "jp-nadda"), _e(2, "jagat-prakash-nadda"), _e(3, "j-p-nadda")]
    linked = {1: ("Q16193764", "alias_exact"), 2: ("Q16193764", "alias_exact")}
    groups = fold_groups(ents, linked)
    assert len(groups) == 1 and len(groups[0]) == 3


def test_curated_spelling_variants_group():
    """Devanagari romanisation is not standardised, so जनता arrives as both "Janta"
    and "Janata". Those are not separator-identical and Wikidata records only one,
    so neither of the other two keys can join them — and the product was showing
    "Cockroach Janata Party" and "Cockroach Janta Party" in one story's cast."""
    ents = [_e(1, "cockroach-janata-party", 212), _e(2, "cockroach-janta-party", 172)]
    assert len(fold_groups(ents, {2: ("Q139857349", "alias_exact")})) == 1


def test_a_curated_group_is_still_refused_on_a_qid_conflict():
    """Curated judgement does not outrank Wikidata saying "two distinct items"."""
    ents = [_e(1, "cockroach-janata-party"), _e(2, "cockroach-janta-party")]
    linked = {1: ("Q1", "alias_exact"), 2: ("Q2", "alias_exact")}
    assert fold_groups(ents, linked) == []
