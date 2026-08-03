"""Hand-labelled STORY boundaries — which events belong to one story.

This is the layer-2 counterpart to tools/gold_pairs (layer 1, article -> event).
Until this existed there was NO ground truth for the story layer, and every
threshold on it was chosen by staring at structural proxies — blob counts, largest
story size. That is how PARTITION_MIN_EDGE_WEIGHT got picked twice with opposite
results and no way to say which was better.

Labelled 2026-08-03 off the current partition run, from the four groups holding the
Cockroach Janta Party coverage plus the Kerala group they leak into. Chosen
deliberately: this is where the product visibly fragments, and it contains BOTH
failure directions in one slice — one real story split across groups, and unrelated
events fused into one.

    partition group 6  -> police force at the protest, + Wangchuk, + one crash report
    partition group 0  -> the paper-leak bill, + two unrelated bills, + hockey
    partition group 4  -> Kerala politics, + Greta backing CJP, + D. Raja
    partition group 28 -> European wildfires (correct, and a clean negative control)

HOW TO READ IT. Same caution as gold_labels: this is a regression suite for one
failure mode, not a corpus sample. It is drawn from ONE topic cluster, so it says
nothing about sport, markets or cyber. Quote it as "the CJP slice", never as
"Prism's story accuracy".

AMBIGUOUS PAIRS ARE NOT SCORED, and that is the point. "Is the metro-station
closure part of the police-force story, or its own?" has no defensible answer, and
a gold set that pretends otherwise would punish a correct algorithm for a coin
flip. Every cross-cluster pair listed in AMBIGUOUS is skipped by pairs(). What is
left is the set of calls a person would make the same way twice.

The granularity target is Story Forest's measured distribution (Liu et al., CIKM
2017): mean 4.07 events per story, median 3, max 25. The clusters below sit in that
range on purpose. Prism's current partition runs median 2 / max 70 — dust and blobs
— which is the shape a single modularity resolution produces and cannot fix
(Fortunato & Barthelemy, PNAS 2007: modularity cannot resolve communities below a
size that scales with the whole graph).
"""

from __future__ import annotations

import itertools

# story key -> event ids. Singletons are real one-event stories here and exist to
# serve as negatives; they are not claims that the story can never grow.
STORIES: dict[str, list[str]] = {
    # --- the CJP protest and the force used against it -----------------------
    "cjp-police-force": [
        "6b6b6179-ac37-4b50-bbdd-f377106447c6",  # Pellet guns, shock batons used against protesters
        "b47c6b07-dd7a-495e-b0b5-c2dac601ac9b",  # 2 protestors injured; 21-year-old on ventilator
        "a9c7fa1a-2acb-4852-92a1-a17afd9f14fd",  # AISA alleges crackdown, seeks release of detained
        "b6f4f47f-c7a3-4064-9f1f-b48a4105ac07",  # RAF fired pellets on orders of Delhi cop
        "09e32210-f7c9-4ecb-b006-a4293d4035c7",  # Delhi ACP hit by stone — the police side of it
        "f51e5827-202f-4456-a154-43fe281abe42",  # SC orders states to release protesting students
        "31b3dd84-b16d-4564-bab8-f77eb9634168",  # Delhi court cancels NBWs against student leader
    ],
    "cjp-metro-closure": [
        "0317e306-ecc5-44dc-b2f9-7472e8a34554",  # CJI on Delhi metro station closures
        "9fe4c8e3-b6e7-49af-9c34-36cbbf0c6929",  # Bar Association: closures affecting lawyers
    ],
    "wangchuk-hunger-strike": [
        "41348513-9bfa-49a0-bf39-e4f094cbc478",  # AIIMS & Safdarjung residents seek Prez intervention
        "bc5cc143-f430-4d88-acb3-bb39ed00c4da",  # Wangchuk's vital parameters remain stable
        "b9a14cd0-cecc-4eaf-af8b-628b95b40dc6",  # Nadda, Jitendra Singh meet Wangchuk at Medanta
        "83825e83-0667-4ded-a230-e5bec800a114",  # CJP calls on Wangchuk to end hunger strike
        "d5fb84cf-dcab-4430-ba65-7a60966b5fdf",  # Opposition MPs meet Wangchuk at hospital
    ],
    # --- the paper leak and the law it produced ------------------------------
    "neet-paper-leak-bill": [
        "0d09c82b-0e49-4418-bdd3-f4cca0990b08",  # Pawar, Kejriwal visit Jantar Mantar after crackdown
        "e796bf8b-ba3d-4abf-88bf-12b3d5d5b1dd",  # Rahul, opposition wear black in Parliament
        "4985936d-14e6-4ba2-83ca-cebfe8f9522c",  # Modi announces fast-track courts for paper leak
        "206c1c57-f66a-40c4-8f94-2a53a2042059",  # Nilekani to lead exam reforms
        "fb89bbec-c038-48c7-86e9-2500ede5fb3a",  # Birla gives 3 hours to settle anti-paper-leak debate
        "0c136d50-b402-4d12-997f-9399da5a5a9e",  # Parliament to debate tougher anti-paper leak bill
        "dad1a2d4-8fbb-49b1-935a-b0cc2d6fe59d",  # BJP MP praises new exam law
        "d9887ff1-90d0-4318-af37-39558c78e205",  # Parliament clears anti-paper leak bill
        "56534964-54f3-40f4-8bef-63a3349ceb37",  # Opposition to keep pressure on Shah in the debate
    ],
    "pradhan-resignation": [
        "f3a2e150-4e10-4d88-8c38-877f2e467fc6",  # BJP's rousing Parliament welcome for ex-edu minister
        "09630d04-c01b-451d-b996-bc29233ca3e9",  # CPI slams BJP for felicitating Pradhan after resigning
    ],
    # --- other business of the same Parliament, which is NOT the same story ---
    "vande-mataram-bill": [
        "568c2808-04c1-4023-89b5-83a277e73f6f",  # Bill making insult to Vande Mataram punishable passed
        "7556deb8-f253-4cd9-b2d3-83eeb5934237",  # Parliament passes Vande Mataram bill
    ],
    "hockey-saffron-jersey": [
        "61d52f33-ba2f-4b33-ab1f-d4ea9855ac04",  # Patnaik hits out at hockey's saffron jersey
        "c74adc50-4069-4851-84fc-5d9a1c545100",  # Oppn attacks BJP for India Hockey's saffron jersey
    ],
    # --- clean negative control: correctly grouped, unrelated to everything ---
    "european-wildfires": [
        "53ccf38d-f6c7-4eab-9164-f6849789e8cf",  # France battles wildfires, Macron emergency meeting
        "122cdf40-ca2b-40ab-8351-3ed702794bd6",  # Wildfires in Spain and France stabilize
    ],
    "kerala-police-leadership": [
        "004ca81e-73fb-4c6a-a496-e380ca811315",  # Kerala government in a quandary over DGP appointment
        "ee1ff133-b782-4d85-b96f-301f0b91d2d4",  # ADGP Ajith Kumar submits explanation
    ],
    # --- one-event stories, all currently fused into a group above -----------
    "ai171-crash-report": ["370267a2-7105-49d8-818d-03374bd1a83c"],
    "panchayat-powers": ["b6c516ce-2f17-405b-9374-152ab207e416"],
    "thakur-contempt-notice": ["cf420f49-0b5c-48bc-b28a-8f22b7f21ab5"],
    "pappu-yadav-privilege": ["66714a9b-273a-4af8-9b45-9e42771b30dc"],
    "dipke-degree-row": ["1813d1a4-98d7-4a8a-b214-807786b16162"],
    "yogi-slams-opposition": ["dbc905a3-1e67-4334-9cb8-a3d0a4e48689"],
    "sabarimala-gold-case": ["e2e961c1-e46d-4cc1-9e78-5438efd51bca"],
    "nithin-raj-death": ["950b6ce6-3296-4625-bd7e-dbd5b4fe6085"],
    "mullaperiyar-dam": ["ba2ac5ba-5567-4812-a98f-bc2825a0671f"],
    "kerala-floods": ["c9ee0e27-2838-4189-8461-e20143b25f27"],
    "kafir-screenshot-case": ["792b7346-90d9-4a32-8146-033c563dcb22"],
    "ksu-railway-blockade": ["0a663a6b-fa4f-4f27-8126-82786fa3e81e"],
    "d-raja-communist-movement": ["e30b5e53-f089-4b16-bdab-83214d3e0e7d"],
    "greta-backs-cjp": ["4748d8a1-71e4-4540-8f1e-ed96daa4ba0f"],
    "nda-families-neet": ["a44bc1a2-024b-4ae5-ad97-3e1b0a46cc9f"],
    "ed-team-attack-bail": ["c57a2ac7-314d-4c85-83f9-8f123d91d2f9"],
}

# Cluster pairs a careful person could call either way. Their cross-pairs are NOT
# scored — a gold set that forces a call here measures the labeller's coin flip.
# All of these are threads of the one protest movement; whether the movement is one
# story or several is exactly the granularity question under test, so it must not
# be smuggled in as an answer.
AMBIGUOUS: set[frozenset[str]] = {
    frozenset({"cjp-police-force", "cjp-metro-closure"}),
    frozenset({"cjp-police-force", "wangchuk-hunger-strike"}),
    frozenset({"cjp-police-force", "neet-paper-leak-bill"}),
    frozenset({"cjp-police-force", "greta-backs-cjp"}),
    frozenset({"cjp-police-force", "nda-families-neet"}),
    frozenset({"cjp-metro-closure", "neet-paper-leak-bill"}),
    frozenset({"cjp-metro-closure", "wangchuk-hunger-strike"}),
    frozenset({"wangchuk-hunger-strike", "neet-paper-leak-bill"}),
    frozenset({"wangchuk-hunger-strike", "greta-backs-cjp"}),
    frozenset({"wangchuk-hunger-strike", "nda-families-neet"}),
    frozenset({"neet-paper-leak-bill", "pradhan-resignation"}),
    frozenset({"neet-paper-leak-bill", "greta-backs-cjp"}),
    frozenset({"neet-paper-leak-bill", "nda-families-neet"}),
    frozenset({"greta-backs-cjp", "nda-families-neet"}),
    frozenset({"pradhan-resignation", "greta-backs-cjp"}),
    frozenset({"pradhan-resignation", "nda-families-neet"}),
    # Kerala's leadership row and the assault case that triggered the explanation.
    frozenset({"kerala-police-leadership", "kafir-screenshot-case"}),
}

STORY_OF: dict[str, str] = {e: k for k, ids in STORIES.items() for e in ids}


def pairs() -> dict[tuple[str, str], bool]:
    """Every scoreable event pair -> whether the two share a story.

    Ambiguous cluster pairs are omitted entirely rather than guessed.
    """
    out: dict[tuple[str, str], bool] = {}
    for a, b in itertools.combinations(sorted(STORY_OF), 2):
        ka, kb = STORY_OF[a], STORY_OF[b]
        if ka != kb and frozenset({ka, kb}) in AMBIGUOUS:
            continue
        out[(a, b)] = ka == kb
    return out


def event_count() -> int:
    return len(STORY_OF)


def story_count() -> int:
    return len(STORIES)
