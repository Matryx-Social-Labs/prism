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
        "d7d5242c-b1ce-4a83-a67f-522342c306c7",  # Congress steps up attack, seeks Pradhan's resignation
        "0be766c9-0f4c-4400-9de0-325608dc3c0d",  # Congress hails Pradhan's resignation
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
    # ── second labelling pass, 2026-08-04 ────────────────────────────────────
    # The first pass was one topic (CJP politics), which is too narrow to select a
    # hyperparameter on: cross-validating a CPM sweep over it produced a config that
    # LOST to production on held-out stories in both fold directions. These clusters
    # come from four other groups in the same run — business, civic infrastructure,
    # electoral politics and sport — so a rule that only works on protest coverage
    # can no longer look general.
    #
    # Three deliberate near-miss sets, because they are what a shared-actor graph
    # gets wrong and a content signal should get right:
    #   - three DIFFERENT bypolls (Bankipur, Datia, Manjalpur) sharing "BJP",
    #     "Congress", "bypoll" and nothing else,
    #   - four BEST bus stories that are one topic and four separate events,
    #   - two India coaching departures that are genuinely separate stories.
    "tn-ford-return": [
        "c8d7b9e1-7ed8-40ad-92c2-0ccc4ea0e17b",  # CM Vijay requests Ford to resume production in TN
        "040ad9d8-71e4-40d3-a683-d6bbf0c8038c",  # Ford delegation meets CM Vijay, discusses expansion
    ],
    "southern-zonal-council": ["e1cf2096-d1b8-4e1c-b8cf-e08028a8c8b9"],
    "tn-investment-mous": ["a00153b9-b47a-4d47-a0af-ef6247618e9f"],
    # One topic ("BEST is failing"), four separate events. The whole group is a
    # worked example of the topic/story confusion.
    "best-fleet-revival": ["b56f7503-f9cc-4d9f-b75c-2702dff31b4b"],
    "best-bus-crash-probe": ["ee43efbd-f38e-46ff-abc6-d7e0e58b29d9"],
    "best-commuter-woes": ["69af6426-795c-4525-9671-81b4f251f851"],
    "best-depot-power-cut": ["c39275bc-f031-468d-89ef-86dcbe80936a"],
    "bankipur-bypoll": [
        "65ea6afd-ece0-4842-b324-f008691f542b",  # Bihar BJP complains to ECI about PK's expenditure
        "62cdf769-e0ed-4ccb-80bc-841db7938d51",  # Nitin Nabin calls PK a businessman
        "766ea6e3-f4b6-4a12-8f73-9f27df7c1254",  # Nitish's appeal for the Bankipur bypoll
        "3187b5c3-82b0-43cd-926a-00460d248dce",  # High drama at Bihar police station, PK claims detentions
        "c43171b8-da55-4042-b920-8a6315a044ca",  # PK wins the seat Nitin Nabin held for 20 years
    ],
    "datia-bypoll": [
        "c4232e50-5707-40ae-8f1b-8483cb71f892",  # Datia bye election campaign
        "1efda373-2950-4e49-823b-076283a38214",  # Datia bypoll: Congress candidate confident
    ],
    "gujarat-manjalpur-bypoll": ["aa44e4fd-15f7-4dd1-8932-3cab630a40c4"],
    "maliwal-punjab-paper-leaks": [
        "973f867e-70db-41cd-944f-5c76eef0d242",  # Maliwal's allegation against Kejriwal on Punjab leaks
        "b602d92f-8f7f-4a44-85d3-6c03b14e8a0d",  # 'Six major paper leaks in five years in Punjab'
    ],
    "punjab-edu-minister-protest": ["1dfc88b2-7504-41e0-ad86-15aad1e9e2ee"],
    "delhi-bjp-youth-outreach": ["f10b7318-b738-4803-b238-15a87e0f44bf"],
    "channi-faridkot-rally": ["6261c07b-6e60-4bf1-b6ad-e3f138712660"],
    "karnataka-cabinet-expansion": [
        "91456068-eb82-4ac8-b943-969ba7230c09",  # Cabinet expansion postponed again
        "72fa073a-612c-4ab7-9d90-83fb3480eeb6",  # 2 Congress MLAs resign over non-inclusion
        "a72325d8-a265-43b7-bf77-cc59a40aa80f",  # 20 names approved by the high command
        "c3de83eb-c381-4c48-8030-f0e06f039639",  # 20 MLAs sworn in
    ],
    "zimbabwe-series-sweep": [
        "188b10f8-4414-48a3-8901-a29b0dd5aa0c",  # Shreyas continues the Dhoni trophy tradition
        "33194c29-f0ac-4beb-897e-bdbd0fefa24b",  # Iyer credits Laxman after the 3-0 sweep
    ],
    "sri-lanka-test-squad": [
        "7462bb6c-24f4-4734-9e9c-6ecacd68f3b3",  # Squad announced for the Sri Lanka tour
        "9e110a2c-8140-4dee-aa53-d9dcb76ad6f1",  # Jadeja returns; Bumrah picked with a rider
        "22a22749-41a2-40fd-abb5-3bac6ac804a3",  # Bumrah ruled out of the Sri Lanka Tests
    ],
    # Two coaching departures, four weeks apart, different people. Same topic
    # ("India's support staff is churning"), different stories.
    "india-fielding-coach-change": [
        "776f9005-92d2-4632-9db9-b1204663f20c",  # Subhadeep Ghosh replaces T Dilip as fielding coach
        "a870868f-5e07-4dd7-a6d0-188c0cd7f126",  # Rohit reacts to Dilip being released
    ],
    "ten-doeschate-exit": [
        "0599ca3f-b3d2-459a-9b06-4dbd7580270a",  # Assistant coach resigns suddenly
        "d22b5a30-07cd-4cca-b963-f5f79489710d",  # Why ten Doeschate parted ways with the team
    ],
    "pandya-ipl-move": ["96b8ad45-bffd-4420-9c26-1f6b726c4556"],
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
    # --- second pass ---------------------------------------------------------
    # Whether the wet-lease fleet's failures and the plan to replace it are one
    # story is exactly the granularity question; do not answer it in the labels.
    frozenset({"best-fleet-revival", "best-commuter-woes"}),
    # Two departures from the same support staff in the same window.
    frozenset({"india-fielding-coach-change", "ten-doeschate-exit"}),
    # Paper leaks reach the labels from two directions — the NEET leak that drove
    # the protest, and Punjab's own leaks used as a political counter-attack.
    # Related enough that a reasonable person could group them.
    frozenset({"maliwal-punjab-paper-leaks", "punjab-edu-minister-protest"}),
    frozenset({"maliwal-punjab-paper-leaks", "neet-paper-leak-bill"}),
    frozenset({"punjab-edu-minister-protest", "neet-paper-leak-bill"}),
    frozenset({"punjab-edu-minister-protest", "pradhan-resignation"}),
    # "After Gen-Z stir, Delhi BJP eyes youth outreach" IS a response to the protest.
    frozenset({"delhi-bjp-youth-outreach", "cjp-police-force"}),
    frozenset({"delhi-bjp-youth-outreach", "neet-paper-leak-bill"}),
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


# --- the corpus sample (batch OkY3sDj_iuiQ, labelled 2026-09-01..03) ----------
#
# THE CJP SLICE ABOVE IS A REGRESSION SUITE FOR ONE FAILURE MODE. This is the
# thing it says it is not: a sample drawn across the corpus — business, cyber,
# sports, health, politics — so it can be quoted as story accuracy rather than as
# one topic cluster.
#
# Two labellers, independently, through the labelling page; every one of the 123
# tasks was seen by both. A candidate joins a story only when BOTH gave a definite
# answer and BOTH ticked it, so these 30 are unanimous.
#
# AGREEMENT, stated because a gold set is only as good as it: per-candidate 0.904
# over 69 comparable tasks, Cohen's kappa 0.593 — moderate, well above chance.
# Exact-set agreement was 52%, which sounds alarming and is the wrong lens: with
# ~10 candidates a task, one differing tick fails the whole set.
#
# THE TWO LABELLERS LEAN DIFFERENTLY and it did not close over the batch: 112
# ticks against 68 on identical tasks, one lumper and one splitter. That lean is
# why CORPUS_DISPUTED exists rather than being folded into the negatives.
#
# Granularity lands where Story Forest says it should without being told to:
# median 3, mean 3.13, max 7 (published: median 3, mean 4.07, max 25). No blobs,
# no dust — independent evidence the labelling is sane.
#
# WHAT IT DOES NOT COVER. 61 of the 246 responses were "I can't read this" —
# Kannada, Devanagari and Tamil headlines neither labeller could assess. Those
# tasks are absent here, so this set is thinner on Indic-language stories than the
# corpus is, and it CANNOT be used to argue the story layer handles them.
CORPUS_STORIES: dict[str, list[str]] = {
    "corpus-001": ["04e3af91-9d85-49ad-b399-bb0520cabb76", "628d4261-1878-4569-9383-f386961ef89e"],
    "corpus-002": ["095ebf63-8da9-478b-a6cd-47887894980e", "4d648c2e-3575-4ea7-9f10-24109b5b43b2", "4fb01c9f-526b-4522-bb65-c3e74e27dced", "6b4cd43f-db6c-4e49-b8e4-d51bc8ecfd3f", "8a61dfa2-4037-4b8d-9eb8-361966f48cd4", "a275df34-62a8-45dc-aeaf-9b44123c88f3", "ae00749c-0da9-4628-ba23-b4527c693fda"],
    "corpus-003": ["0c4f8491-da18-4ff3-980d-91a6c3fb54d7", "3f07260c-796f-475e-9520-b901e2b07f50", "b26e5b3d-f947-4682-90d0-4fc643422ee6"],
    "corpus-004": ["103b5245-170f-44c3-ada8-34e35b398436", "c125fc27-6cb5-4c91-bea4-f94e0ee2ea87"],
    "corpus-005": ["16714d9f-6115-456e-a7d0-6e201b5b88b5", "6fa078c6-fb7b-46ec-af2d-4c58adcb83b6"],
    "corpus-006": ["1f70d001-95df-435d-9419-1e6a11809c8f", "9f547fa0-4299-4f4a-9205-40f8edc86800", "a15afe1c-2adf-4f84-9ad1-54298ea91915", "56147b89-91b9-422f-b313-896a8ef0386f", "f29da7b4-dbf4-4e84-accb-6a5464f995ea", "d680f446-e35b-4500-b836-35d10751c4ea"],
    "corpus-007": ["22e469d5-e427-4fc5-a4d4-4237c6779b48", "da4bbd00-ed2b-4185-8213-b346225dfa1f"],
    "corpus-008": ["28f88ec4-8960-46b8-b489-303eb7a3bc7f", "e0fbf2ae-74eb-4422-9f1c-6f3f4a53b57c", "252db0aa-2a51-4620-8475-73ad6af3f296"],
    "corpus-009": ["2d85bc33-56aa-4133-a71c-0219d4ffff2a", "a3a7e293-4a03-4595-a875-6e8c11480d55"],
    "corpus-010": ["49f9534c-2b60-4429-bc7f-9ef4facb1d60", "2cd84150-b671-485e-a620-8dd2bea48764"],
    "corpus-011": ["5e82eb16-dd75-4b3e-9b1e-eebfd824e3cb", "36ed2be9-9f75-47e6-9829-10f84527d15c", "d2522761-7176-4e2a-92c7-eb3a1c0de2ff", "dc6a7b16-d479-4045-b066-1bab2af27eef"],
    "corpus-012": ["64a5168a-3a67-483d-9f76-639e0b79cb78", "5b41dcab-092f-4381-b2f9-febd8aa9cc2d", "33e7a5d0-1933-44d4-aa67-ae4fdd5ae9a2"],
    "corpus-013": ["68ff78c5-452e-4c14-970b-07651ee29ef8", "613ee07d-8da9-4533-b9de-873ec21f1d5b", "460bdb43-2628-41b7-9fdc-45d4889c0080", "ddd63ff6-9a01-4e23-986b-e4c0973f0b51", "2528fb9e-b63b-495e-aabb-366359257fe4"],
    "corpus-014": ["70165b28-e514-4814-ac82-08a4c878f93d", "82f88ecd-d42e-4324-9332-942773929a93", "1d99b849-0a10-481d-85b8-dfa7cf599068"],
    "corpus-015": ["89587a20-6aa8-40ce-8bd7-83792283c83f", "1b4137a9-7bdf-4e8b-9c98-2d5d1fd9b146"],
    "corpus-016": ["92763a3c-fc95-4028-8670-987a9d875a46", "50040fe7-0c1b-4a66-aa85-0b1664f0443b", "6fb8d354-dcc7-4133-8570-94216b2ef47f", "ee293fc9-404f-4a4a-8274-8fb7707fbc98"],
    "corpus-017": ["9322e0df-58b6-4167-8447-7acc56c9567e", "e50c4158-db39-458d-a845-baf1b9e97a17"],
    "corpus-018": ["95eaf3cd-8213-41ae-bdd6-70bd1683edd2", "309c9768-c70f-4524-aad5-e583e284dc38"],
    "corpus-019": ["9d236dbc-baf4-4a48-8f5f-46bd07f77ed3", "15ab93e0-7b2c-4431-bde3-0e89ecd36584"],
    "corpus-020": ["a1444e89-7e8d-406c-89a5-81170b9a4dca", "21a2b95a-924e-4120-8fb5-0b18a362d16d", "d46628ca-6e22-459c-8874-606fdecd6150"],
    "corpus-021": ["a15afe1c-2adf-4f84-9ad1-54298ea91915", "1f70d001-95df-435d-9419-1e6a11809c8f", "d680f446-e35b-4500-b836-35d10751c4ea"],
    "corpus-022": ["acd695a4-8fa3-48d8-810a-0e2b4e30980f", "76b62065-9fcf-49b1-b702-5e66b3aeefa8", "d7faf9ff-5c3a-48e7-93e7-0945b7832cdd"],
    "corpus-023": ["c87e148f-518d-4748-889a-df4d4709cf94", "f746abde-b04f-4194-898f-4a9b09571e8b"],
    "corpus-024": ["cf2c3b71-cf09-433e-acd1-18bd101c40c0", "35f3d046-69e4-4cd5-9f62-9d698e3f223f"],
    "corpus-025": ["dc1981d5-72e2-4e4e-93b9-b75a46f61853", "50f5a5b5-77b8-47c2-83c2-e88cb2a75c81", "b7b76b93-6609-4bff-b7ea-1b66cdf874c1", "f96e8535-7066-4ab0-85b8-03c53a493f1c", "3ff253ad-b547-4cd5-8628-ab2143329d76", "a8591f4e-256d-41c3-a839-0d8818fe5521"],
    "corpus-026": ["df2c5f3f-d744-420c-b46c-4defb5f6287f", "ce85db85-ca18-4ec8-99d6-10765f959a26", "68c19336-cb65-4295-ad1f-7b10c79c51e0", "73a7f63f-88c2-456b-8dfa-0e87aa483a83", "3abd8a01-a1fe-4e7b-b841-afd7e3abb5a4", "e10921a2-e98d-4e03-a38c-92753d5c5018"],
    "corpus-027": ["ef56360c-35d8-41dd-9f8d-1e9848565a07", "c7060901-cc08-4bd3-8742-25c3ee17cff3", "04204680-bf39-4fbf-93cf-2519299b6ad5", "821a96e7-9f27-4bc1-862a-65bf71c5b92a"],
    "corpus-028": ["f746abde-b04f-4194-898f-4a9b09571e8b", "68f2ce19-d32d-488f-a80d-6dcfe7d08ae1"],
    "corpus-029": ["fb90bf47-f090-4aa5-8994-57f2a6f224e4", "7e26ca31-4b44-4e15-ba73-a96856770bc2"],
    "corpus-030": ["fbb3901b-9da7-48ab-bd39-6a6651aa903d", "a6d43fd4-0733-45ad-880e-b3e856520857", "d46628ca-6e22-459c-8874-606fdecd6150"],
}

# Pairs where one labeller ticked and the other did not, both having given a
# definite answer. Recording these as negatives would assert a boundary two
# careful people disagreed on — the same coin flip AMBIGUOUS refuses above. 67 of
# them, excluded from scoring rather than guessed.
CORPUS_DISPUTED: set[frozenset[str]] = {
    frozenset({"095ebf63-8da9-478b-a6cd-47887894980e", "24ec70a8-7362-49dd-9480-515d69774bd5"}),
    frozenset({"095ebf63-8da9-478b-a6cd-47887894980e", "6aa91264-963c-49a6-b8e4-c8aaf03b40fa"}),
    frozenset({"095ebf63-8da9-478b-a6cd-47887894980e", "6bc90c20-2bb0-49e1-acc0-21b22c5abbdf"}),
    frozenset({"11166757-4c0a-468d-9258-3f22321fd1c5", "4d130f4e-610b-4684-8907-d16949ee7803"}),
    frozenset({"11166757-4c0a-468d-9258-3f22321fd1c5", "8f7de710-2987-4ab9-9027-93b528779554"}),
    frozenset({"1ec0732d-2cb3-4c34-8d4c-0fa8c39c95e2", "3e8757a6-fadc-40a2-a857-9ba03ed7da81"}),
    frozenset({"1f70d001-95df-435d-9419-1e6a11809c8f", "c70c1c13-66ce-4054-a822-ea1605682202"}),
    frozenset({"22e469d5-e427-4fc5-a4d4-4237c6779b48", "a60062d0-af2f-4d7b-98b0-070c9d7cf47a"}),
    frozenset({"2b765b2b-3087-4817-ad19-6415dd67f8e4", "acef882e-ca0c-4498-b3e9-4f3a7cc40649"}),
    frozenset({"2d85bc33-56aa-4133-a71c-0219d4ffff2a", "2f85738d-204a-4986-890a-3dd395408340"}),
    frozenset({"3de5434d-68be-403b-9e46-81c97e2cd97e", "3526a777-6e9b-48cc-aed5-547897c14500"}),
    frozenset({"3de5434d-68be-403b-9e46-81c97e2cd97e", "95423eae-2c75-43fe-92b7-202a3c96b23d"}),
    frozenset({"4f6d28fb-4f2c-4977-8ff7-6597a01a106f", "46526919-75e6-492d-9780-285d1e736b07"}),
    frozenset({"5cb2dfc1-c7c9-4537-ac4b-273df5367880", "6c745b3f-4f88-4341-9a29-f9108e8f2325"}),
    frozenset({"5cb2dfc1-c7c9-4537-ac4b-273df5367880", "95c9f26c-40c2-410b-b93b-b6c0ffa88e12"}),
    frozenset({"5e82eb16-dd75-4b3e-9b1e-eebfd824e3cb", "3778c303-9d31-4a0d-82af-ad5496c0c2ba"}),
    frozenset({"5e82eb16-dd75-4b3e-9b1e-eebfd824e3cb", "7ddcdd61-865d-4974-82aa-a901e4b482a8"}),
    frozenset({"5e82eb16-dd75-4b3e-9b1e-eebfd824e3cb", "7efe9aad-9a72-450d-8f6f-a7f4613434b7"}),
    frozenset({"5e82eb16-dd75-4b3e-9b1e-eebfd824e3cb", "c0dcb797-4ecd-4658-af69-1028b9796cab"}),
    frozenset({"64a5168a-3a67-483d-9f76-639e0b79cb78", "ae53f752-c287-4b30-8705-746a4cd3e07b"}),
    frozenset({"6c429155-6a20-415e-986f-0403927cd848", "39dcadfe-ba4d-4408-809b-badc9e4d4127"}),
    frozenset({"6c429155-6a20-415e-986f-0403927cd848", "4122c08f-0946-46b6-9db1-25ad4362a12a"}),
    frozenset({"70165b28-e514-4814-ac82-08a4c878f93d", "1d99b849-0a10-481d-85b8-dfa7cf599068"}),
    frozenset({"70165b28-e514-4814-ac82-08a4c878f93d", "82f88ecd-d42e-4324-9332-942773929a93"}),
    frozenset({"7674f7a3-b21a-412f-8c39-d6e2c828f26b", "6e74e1ea-dde5-4a5a-8c94-39cf18fe7b21"}),
    frozenset({"7674f7a3-b21a-412f-8c39-d6e2c828f26b", "c1ef2696-de8a-40e7-b947-4c8890e2cdda"}),
    frozenset({"89587a20-6aa8-40ce-8bd7-83792283c83f", "15b0b82c-4af0-4c80-a80c-2ce6cac58507"}),
    frozenset({"89587a20-6aa8-40ce-8bd7-83792283c83f", "3a18782f-8c12-4aff-adee-5e772073dad5"}),
    frozenset({"89587a20-6aa8-40ce-8bd7-83792283c83f", "540595e2-772d-46f4-809c-4cfa5dac58c7"}),
    frozenset({"89587a20-6aa8-40ce-8bd7-83792283c83f", "9f9d085d-b3f2-4e0a-8fa3-4bacd60731db"}),
    frozenset({"89587a20-6aa8-40ce-8bd7-83792283c83f", "b798f41b-621c-4344-b1cf-995014427797"}),
    frozenset({"8bff4d46-ffd5-44f4-bf71-15fbe0f3c588", "0e1eb5f9-1008-4d6c-bc3f-ced285a6c1fb"}),
    frozenset({"92763a3c-fc95-4028-8670-987a9d875a46", "086fcf0c-6dff-44b5-9b33-a0f3a9822797"}),
    frozenset({"92763a3c-fc95-4028-8670-987a9d875a46", "2cb3d189-eeed-43fa-b3a7-5e0d9b82f2a8"}),
    frozenset({"92763a3c-fc95-4028-8670-987a9d875a46", "83eab5d0-6e0e-4df1-8bc4-cfd82986d449"}),
    frozenset({"9322e0df-58b6-4167-8447-7acc56c9567e", "3756e387-78e2-4dba-a5f9-f49bdb6d78c5"}),
    frozenset({"9322e0df-58b6-4167-8447-7acc56c9567e", "aa6a75fe-a78e-4066-87b8-11afcf46b688"}),
    frozenset({"9322e0df-58b6-4167-8447-7acc56c9567e", "eaa1d134-d3b4-4b43-9a9d-04fd6a2f1b43"}),
    frozenset({"9d236dbc-baf4-4a48-8f5f-46bd07f77ed3", "5d874531-c3d9-4d97-946a-0ca15a33b806"}),
    frozenset({"9d236dbc-baf4-4a48-8f5f-46bd07f77ed3", "81462ac3-ca24-4cda-9447-81c9ed85ec9b"}),
    frozenset({"9d236dbc-baf4-4a48-8f5f-46bd07f77ed3", "be750b01-7d5a-46a9-9891-492b0d24af73"}),
    frozenset({"a15afe1c-2adf-4f84-9ad1-54298ea91915", "9f547fa0-4299-4f4a-9205-40f8edc86800"}),
    frozenset({"a1819226-d6c4-472a-98a0-fee6acc0846b", "3de5434d-68be-403b-9e46-81c97e2cd97e"}),
    frozenset({"a1819226-d6c4-472a-98a0-fee6acc0846b", "95423eae-2c75-43fe-92b7-202a3c96b23d"}),
    frozenset({"c87e148f-518d-4748-889a-df4d4709cf94", "68f2ce19-d32d-488f-a80d-6dcfe7d08ae1"}),
    frozenset({"cb90219f-9aca-4cce-9267-3b332a511072", "a890925a-9cf9-4bb8-89ab-968e4ca0ff1b"}),
    frozenset({"cb90219f-9aca-4cce-9267-3b332a511072", "ffc2d220-a8d7-4313-afe2-9d3ade032426"}),
    frozenset({"dc1981d5-72e2-4e4e-93b9-b75a46f61853", "3482c856-ca5e-4fc1-90c5-0af7c304381d"}),
    frozenset({"e1de8d64-80e3-4f02-b2a9-9320012084e3", "19bb4fec-699d-4683-8d4d-2f4558b8f44e"}),
    frozenset({"e1de8d64-80e3-4f02-b2a9-9320012084e3", "21441549-5fc1-440a-babb-2956e1675020"}),
    frozenset({"ef56360c-35d8-41dd-9f8d-1e9848565a07", "097d4f9b-d726-47a2-8490-6c5efaa82488"}),
    frozenset({"f61c4d73-d5a4-4a86-bd40-629aa33a7c05", "06726a0a-f739-4850-aa1d-eedd3adefdaa"}),
    frozenset({"f61c4d73-d5a4-4a86-bd40-629aa33a7c05", "20a45197-1513-4997-80a1-b846e9e33edc"}),
    frozenset({"f6b5066d-7707-48ab-b4e3-9747f33a0d04", "c0e5941a-bf3f-4a22-91e0-ceb629170b68"}),
    frozenset({"f746abde-b04f-4194-898f-4a9b09571e8b", "0ecb63b0-14f7-4a97-afde-5c7ec0e90d6b"}),
    frozenset({"f746abde-b04f-4194-898f-4a9b09571e8b", "c87e148f-518d-4748-889a-df4d4709cf94"}),
    frozenset({"fa0a1268-0a60-4ccb-8a39-e716283f2ce7", "2d70e2e6-5363-445c-a2b9-07b49d441faf"}),
    frozenset({"fb90bf47-f090-4aa5-8994-57f2a6f224e4", "143e70da-dd5d-4238-ba05-79e0ff2dfdd4"}),
    frozenset({"fb90bf47-f090-4aa5-8994-57f2a6f224e4", "dd2bff83-16a6-477f-a85b-37bc27bd26fa"}),
    frozenset({"fb90bf47-f090-4aa5-8994-57f2a6f224e4", "fc1ae27a-1416-4459-ab48-1bc18356cfa2"}),
    frozenset({"fbb3901b-9da7-48ab-bd39-6a6651aa903d", "13bae184-c5d7-4661-97d2-d5500611eb9a"}),
    frozenset({"fbb3901b-9da7-48ab-bd39-6a6651aa903d", "c2958b17-8aa9-4704-a1a0-e732500c62fa"}),
    frozenset({"fbb3901b-9da7-48ab-bd39-6a6651aa903d", "d37c9697-9e12-4a48-99a3-7ce51ac9c8ad"}),
    frozenset({"fbb3901b-9da7-48ab-bd39-6a6651aa903d", "ea67d94a-0e38-4ccb-868f-0c6dd740660d"}),
    frozenset({"fe0460ed-c98c-40a9-a82e-5518b59c8bc0", "33cb0135-df34-4613-9f78-b2cdd359e526"}),
    frozenset({"fe0460ed-c98c-40a9-a82e-5518b59c8bc0", "5f92127f-e4cf-4167-bd6d-c046df4e9327"}),
    frozenset({"fe0460ed-c98c-40a9-a82e-5518b59c8bc0", "73db057a-567d-43fe-a9fa-f1871235b584"}),
}

CORPUS_STORY_OF: dict[str, str] = {e: k for k, ids in CORPUS_STORIES.items() for e in ids}


def corpus_pairs() -> dict[tuple[str, str], bool]:
    """Every scoreable pair in the corpus sample. Disputed pairs are omitted."""
    out: dict[tuple[str, str], bool] = {}
    for a, b in itertools.combinations(sorted(CORPUS_STORY_OF), 2):
        if frozenset({a, b}) in CORPUS_DISPUTED:
            continue
        out[(a, b)] = CORPUS_STORY_OF[a] == CORPUS_STORY_OF[b]
    return out
