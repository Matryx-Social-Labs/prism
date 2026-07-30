"""Hand-labelled gold clustering for the six largest production events.

Labelled 2026-07-30 by reading all 171 article titles in publication order. The
label is the real-world event a reader would say the article is about, so two
articles share a label iff a reader would expect to find them on one page.

WHY THESE SIX: they are every production event with >=20 members, i.e. the ones
where over-merge is worst. That makes this a REGRESSION SUITE for fusion, not a
representative sample of the corpus. B-cubed recall computed over it is close to
meaningless (almost everything here is over-merged, so recall starts near 1.0);
B-cubed PRECISION, macro purity, and the cluster count are the numbers to watch.
A random-sample set is still needed before anyone claims a headline F1.

Some labels span predicted events on purpose. `courts-police-action` appears in
both event 1 and event 6, `kangana-row` in events 1 and 2, `kharge-shah` in 1 and
2. Those are real FRAGMENTATION — the same story split across clusters — and they
are what gives this set any recall signal at all.

Judgement calls worth knowing about, since a different annotator would differ:
- Distinct legal proceedings are distinct events. The metro-closure plea, the
  internet-shutdown plea and the surveillance plea are separate from the main
  police-action litigation even though all four arise from one protest.
- A roundup that leads on one event is labelled as that event, not as its own
  thing (the nationwide-rain piece leading on the Assam toll is `assam-floods`).
- Opinion and analysis about an event belong to the event.
"""

# predicted event id prefix -> {index in publication order: gold label}
# Index order is by published_at within each predicted event, as exported.
GOLD: dict[str, dict[int, str]] = {
    # ── 49 members: the CJP/Jantar Mantar protest, plus ~20 other stories ──
    "1ffa4ca9": {
        0: "cjp-protest-day1", 1: "cjp-protest-day1", 2: "parliament-adjourn",
        3: "cjp-protest-day1", 4: "cong-dharna", 5: "hyderabad-solidarity",
        6: "cjp-protest-day1", 7: "wangchuk-hospital", 8: "wangchuk-hospital",
        9: "black-day-protest", 10: "kangana-row", 11: "wangchuk-hospital",
        12: "courts-police-action", 13: "courts-police-action",
        14: "cjp-protest-ongoing", 15: "cjp-protest-ongoing", 16: "lamba-slap-video",
        17: "pradhan-resignation", 18: "aisa-activists", 19: "police-criminal-ident",
        20: "greta-backs-protest", 21: "courts-police-action", 22: "pradhan-welcome",
        23: "cjp-fir-withdrawal", 24: "kangana-row", 25: "kangana-row",
        26: "cjp-fir-withdrawal", 27: "cjp-fir-withdrawal", 28: "cjp-fir-withdrawal",
        29: "bihar-cop-ak47", 30: "kangana-row", 31: "junaid-video",
        32: "cjp-legal-aid", 33: "cjp-fir-withdrawal", 34: "pradhan-welcome",
        35: "cjp-fir-withdrawal", 36: "cjp-fir-withdrawal", 37: "cjp-fir-withdrawal",
        38: "cjp-saakshi", 39: "courts-police-action", 40: "kangana-row",
        41: "kangana-row", 42: "kangana-row", 43: "kangana-row", 44: "kangana-row",
        45: "cjp-fir-withdrawal", 46: "cjp-fir-withdrawal", 47: "kharge-shah",
        48: "neet-cases-closed",
    },
    # ── 33 members: Parliament / anti-paper-leak bill, plus ~13 others ──
    "226a3dfa": {
        0: "cjp-govt-talks", 1: "opposition-rift", 2: "cjp-govt-talks",
        3: "opinion-democracy", 4: "cjp-govt-talks", 5: "cjp-govt-talks",
        6: "bams-paper-leak", 7: "parliament-adjourn", 8: "punjab-paper-leak",
        9: "punjab-paper-leak", 10: "rahul-meets-irfan", 11: "anti-leak-bill",
        12: "e20-town-hall", 13: "punjab-paper-leak", 14: "parliament-adjourn",
        15: "rahul-meets-irfan", 16: "e20-town-hall", 17: "rahul-meets-irfan",
        18: "punjab-paper-leak", 19: "anti-leak-bill", 20: "rahul-meets-irfan",
        21: "anti-leak-bill", 22: "priyanka-rijiju-spat", 23: "priyanka-rijiju-spat",
        24: "anti-leak-bill", 25: "anti-leak-bill", 26: "anti-leak-bill",
        27: "kharge-shah", 28: "channi-faridkot-rally", 29: "kangana-row",
        30: "rahul-privilege-notice", 31: "anti-leak-bill", 32: "rahul-privilege-notice",
    },
    # ── 25 members: nominally DMK/NEET. Twelve unrelated stories. ──
    "856b61a1": {
        0: "dmk-neet-abolition", 1: "chalo-lok-bhavan", 2: "chalo-lok-bhavan",
        3: "dmk-neet-abolition", 4: "dmk-neet-abolition", 5: "dmk-neet-abolition",
        6: "kargil-vijay-diwas", 7: "mgu-poster-row", 8: "mgu-poster-row",
        9: "mohandas-remark", 10: "mohandas-remark", 11: "d-raja-communist",
        12: "d-raja-communist", 13: "mohandas-remark", 14: "mohandas-remark",
        15: "mohandas-remark", 16: "vanni-arasu-slogan", 17: "vanni-arasu-slogan",
        18: "mohandas-remark", 19: "mohandas-remark", 20: "evm-kolathur",
        21: "ambedkar-photo-ripon", 22: "dmk-thanjavur-protest",
        23: "jantar-trafalgar", 24: "tn-medical-seats",
    },
    # ── 22 members: the Cauvery water dispute, a topic rather than an event ──
    "346030c7": {
        0: "vijay-karnataka-visit", 1: "cauvery-cwrc-order", 2: "cauvery-cwrc-order",
        3: "karnataka-proposals", 4: "karnataka-proposals", 5: "cauvery-cwrc-order",
        6: "cauvery-cwrc-order", 7: "cauvery-cwrc-order", 8: "cauvery-cwrc-order",
        9: "cauvery-cwrc-order", 10: "cauvery-cwrc-order", 11: "cauvery-cwrc-order",
        12: "cauvery-cwrc-order", 13: "cauvery-cwrc-order", 14: "cauvery-cwrc-order",
        15: "vijay-karnataka-visit", 16: "vijay-karnataka-visit",
        17: "vijay-karnataka-visit", 18: "karnataka-drought",
        19: "cauvery-protests", 20: "cauvery-protests", 21: "cauvery-protests",
    },
    # ── 22 members: Assam floods. The cleanest of the six. ──
    "92763a3c": {
        0: "assam-floods", 1: "assam-floods", 2: "assam-floods", 3: "assam-floods",
        4: "assam-floods", 5: "assam-floods", 6: "assam-floods",
        7: "sikkim-tunnel", 8: "sikkim-tunnel",
        9: "assam-floods", 10: "assam-floods", 11: "assam-floods", 12: "assam-floods",
        13: "assam-floods", 14: "assam-floods", 15: "assam-floods", 16: "assam-floods",
        17: "assam-floods", 18: "assam-floods", 19: "assam-floods",
        20: "gujarat-rainfall", 21: "assam-floods",
    },
    # ── 20 members: courts on the protest crackdown. Coherent bar three pleas. ──
    "45120a3b": {
        0: "courts-police-action", 1: "courts-police-action", 2: "courts-police-action",
        3: "courts-police-action", 4: "courts-police-action", 5: "courts-metro-closure",
        6: "courts-police-action", 7: "courts-internet-shutdown",
        8: "courts-surveillance", 9: "courts-surveillance",
        10: "courts-police-action", 11: "courts-police-action",
        12: "courts-police-action", 13: "courts-police-action",
        14: "courts-police-action", 15: "courts-police-action",
        16: "courts-police-action", 17: "courts-police-action",
        18: "courts-police-action", 19: "courts-police-action",
    },
}


def gold_event_count() -> int:
    """Distinct real-world events across the labelled set."""
    return len({label for ev in GOLD.values() for label in ev.values()})


def labelled_article_count() -> int:
    return sum(len(ev) for ev in GOLD.values())
