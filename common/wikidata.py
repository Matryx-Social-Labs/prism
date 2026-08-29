"""Wikidata lookup for the canonical entity spine — QIDs instead of folded strings.

WHY THIS EXISTS. `common/entity_aliases.py` is a hand-maintained list: every
romanisation of every party, added by a human who noticed a split. It cannot scale
and it cannot be multilingual, because it folds STRINGS. Wikidata already holds
the mapping we are hand-writing — Q10225 carries "BJP", "Bharatiya Janata Party",
"Bharatiya Janta Party" and "भारतीय जनता पार्टी" as aliases of one item — so the
list becomes a lookup and the multilingual case comes free.

THE ONE NON-OBVIOUS DESIGN DECISION. Search is used only to FIND candidate items;
it is never trusted to decide a link. Search ranks fuzzily, and top-1 on a fuzzy
rank is how "CJP" silently becomes some unrelated party. So: search finds
candidates, we pull each candidate's OWN surface forms into a local index, and a
link is an EXACT match against that index. Anything less is no link at all, and
`local:<slug>` costs us nothing. Precision over recall is not timidity here — a
wrong fold is unrecoverable once mentions are repointed, and this repo has already
watched fuzzy matching collapse 1638 CVEs into 7.

Measured 2026-08-28, that index reproduces the hand list without being told:

    bjp, bharatiya-janata-party                   -> Q10230
    dmk, dravida-munnetra-kazhagam                -> Q1255973
    भारतीय-जनता-पार्टी, भाजपा, বিজেপি, بھارتیہ-جنتا-پارٹی  -> Q10230

The first two lines are rows we hand-wrote in `entity_aliases.py`. The third is
the multilingual case that list can never cover, because it folds strings in one
script. That is the whole argument for QIDs in one screen.

AND IT RECOVERS WHAT SEARCH CANNOT SEE. The case that motivated this module:

    wbsearchentities("Pakistan Muslim League-Nawaz")  ->  NO HIT
    wbsearchentities("Pakistan Muslim League (N)")    ->  Q799577

Same party, and search finds it under one name and not the other. Q799577's alias
list does not carry the missing form either — but its English WIKI TITLE is
"Pakistan Muslim League – Nawaz", which normalises to exactly the key search
failed on. Search proposes; the index decides; the hyphen-vs-en-dash difference
that defeated string matching disappears in normalisation.

THE LIMIT, stated so it is not discovered later: the index is exactly as good as
Wikidata's coverage. A variant no wiki has ever recorded matches nothing and falls
to `local:<slug>`, which is the correct outcome — a refusal we can see, rather
than a fuzzy guess we cannot.
"""

import json
import urllib.parse
import urllib.request

from common.text import canonical_entity_name, slugify

API = "https://www.wikidata.org/w/api.php"
UA = "Prism/1.0 (news entity linking; +https://www.readprism.news)"

# Wikidata's own languages worth indexing: English plus the languages we ingest.
# An alias in `kn` is what folds a Kannada masthead's spelling onto the same QID.
LANGS = ("en", "hi", "bn", "ta", "te", "kn", "ml", "mr", "gu", "pa", "or", "as", "ur")


def alias_key(name: str) -> str:
    """The index key. Deliberately the SAME normalisation our entities already use
    (`slugify(canonical_entity_name(...))`), so an entity slug looks itself up with
    no second convention to keep in sync — and no class of variant that folds on
    one side of the join but not the other.

    Note this is entity_slug WITHOUT `resolve_alias`: the QID path must stand on
    its own evidence, not lean on the hand list it is replacing. If the two
    disagree that is a finding, and it cannot be one if they share an input.
    """
    return slugify(canonical_entity_name(name))


def _get(params: dict) -> dict:
    q = urllib.parse.urlencode({**params, "format": "json"})
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def search(name: str, *, limit: int = 5) -> list[str]:
    """Candidate QIDs for a surface form. FINDING candidates, not deciding a link."""
    hits = _get({
        "action": "wbsearchentities", "search": name, "language": "en",
        "uselang": "en", "type": "item", "limit": limit,
    }).get("search") or []
    return [h["id"] for h in hits]


def fetch_aliases(qids: list[str]) -> dict[str, dict]:
    """Every surface form an item is known by, batched (the API caps ids at 50).

    Three sources, and the third is not optional. Labels and aliases are the
    obvious ones; SITELINK TITLES are here because Wikidata items can simply lack
    a label in a language they clearly have coverage in:

        Q1058  ->  137 labels, none of them `en`
                   description  "Prime Minister of India since 2014"
                   enwiki title "Narendra Modi"

    That is Narendra Modi, the most prominent entity in an Indian news corpus, and
    a labels-and-aliases index does not contain the string "Narendra Modi" for
    him. He would fall to `local:` and keep splitting — the exact failure this
    module exists to end, on the exact entity where it costs most. A wiki article
    title is also curated, so it tends to be the cleanest form available.

    Titles are restricted to the wikis for languages we ingest and stripped of
    their disambiguating parenthetical ("Rahul Gandhi (politician)"), which is a
    wiki convention rather than part of the name.

    `prior` is the sitelink count — how many Wikipedias carry an article. A weak
    prominence proxy, used ONLY to break a tie when one surface form points at two
    items. Kept deliberately small: a real disambiguator would use context, and we
    have no evidence yet that justifies building one.
    """
    import re

    out: dict[str, dict] = {}
    for i in range(0, len(qids), 50):
        batch = qids[i:i + 50]
        data = _get({
            "action": "wbgetentities", "ids": "|".join(batch),
            "props": "labels|aliases|sitelinks", "languages": "|".join(LANGS),
        }).get("entities") or {}
        for qid, ent in data.items():
            if "missing" in ent:
                continue
            # Kind per surface form, strongest first — a name reached as both a
            # label and an alias is a label. See the disambiguation note above.
            forms: dict[str, str] = {}
            sitelinks = ent.get("sitelinks") or {}
            for group in (ent.get("aliases") or {}).values():
                for a in group:
                    forms[a["value"]] = "alias"
            for lang in LANGS:
                title = (sitelinks.get(f"{lang}wiki") or {}).get("title")
                if title:
                    # The RAW title is a recorded name. The parenthetical-stripped
                    # form is a derived guess and is ranked as an alias, because a
                    # wiki parenthetical is not always a disambiguator: stripping
                    # "Communist Party of India (Marxist)" yields the name of a
                    # different, still-existing party. Ranking the derived form as
                    # strongly as a real title let it tie with the true CPI's own
                    # label and forced a refusal on an entity we can resolve.
                    forms.setdefault(re.sub(r"\s*\([^)]*\)\s*$", "", title).strip(), "alias")
                    forms[title] = "sitelink"
            for lab in (ent.get("labels") or {}).values():
                forms[lab["value"]] = "label"
            out[qid] = {
                "forms": {n: k for n, k in forms.items() if n},
                "label": ((ent.get("labels") or {}).get("en") or {}).get("value", ""),
                "prior": len(sitelinks),
            }
    return out


SPARQL = "https://query.wikidata.org/sparql"


def agent_qids(qids: list[str]) -> set[str]:
    """The subset of `qids` that are people or organizations.

    Our entity table only holds `person` and `organization` rows, so a candidate
    that is neither can never be a correct link — and search happily returns them.
    Measured on this corpus, they are the main cause of false ambiguity:

        "BJP"  ->  Q10230  Bharatiya Janata Party
                   Q919631 British Journal of Pharmacology   <- blocks the link
        "CPI"  ->  ... Q27677677 isolated cleft palate

    Without this filter those force a refusal on entities we can resolve perfectly
    well, and the biggest available IDF fix (BJP, 1.47x) is lost to a pharmacology
    journal. With it, genuine ambiguity still refuses — three different people
    named Amit Shah stay unlinked, which is correct.

    P31/P279* rather than a hand-listed set of types: "political party",
    "government agency" and "trade union" are all subclasses of organization, and
    enumerating that taxonomy ourselves would be the same hand-maintained list this
    module exists to delete. One query answers for every candidate at once.
    """
    out: set[str] = set()
    for i in range(0, len(qids), 200):
        values = " ".join(f"wd:{q}" for q in qids[i:i + 200])
        query = (
            "SELECT DISTINCT ?item WHERE { VALUES ?item {" + values + "} "
            "?item wdt:P31/wdt:P279* ?root . VALUES ?root {wd:Q5 wd:Q43229} }"
        )
        req = urllib.request.Request(
            f"{SPARQL}?{urllib.parse.urlencode({'query': query, 'format': 'json'})}",
            headers={"User-Agent": UA, "Accept": "application/sparql-results+json"},
        )
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.load(r)
        for b in data["results"]["bindings"]:
            out.add(b["item"]["value"].rsplit("/", 1)[-1])
    return out


INDIA = "Q668"


def entity_context(qids: list[str]) -> dict[str, dict]:
    """Liveness and country for candidates, to separate what a name alone cannot.

    Only ever called for candidate sets that are ALREADY ambiguous, so it costs one
    query for a handful of items rather than a property fetch for the whole index.

    Two signals, and the distinction between them matters:

      defunct   P576 (dissolved) for organizations, P570 (died) for people.
      countries P17.

    `defunct` is close to a filter — given a live candidate and a defunct one, a
    current-news corpus means the live one. "Indian National Congress" matches both
    the party in government and a splinter that existed 1969-77, with identical
    labels; nothing in the name separates them and liveness does.

    `countries` is weaker and must never become a blanket preference for India.
    Pakistani, Chinese and American entities are legitimately covered here — PML-N
    resolves to Q799577 precisely because it is unambiguous. Country may only break
    a tie between candidates that a name has already failed to separate, which is
    where "Aam Aadmi Party" (Indian Q129844 vs Pakistani Q17003198) sits.

    Deliberately NOT prominence. That signal is what merged the CPI into the
    CPI(Marxist) on 52 sitelinks against 46, and these two are evidence about which
    entity a story is about rather than about which is more famous.
    """
    out: dict[str, dict] = {q: {"defunct": False, "countries": set()} for q in qids}
    for i in range(0, len(qids), 200):
        values = " ".join(f"wd:{q}" for q in qids[i:i + 200])
        query = (
            "SELECT ?item ?ended ?country WHERE { VALUES ?item {" + values + "} "
            "OPTIONAL { ?item wdt:P576 ?dis } OPTIONAL { ?item wdt:P570 ?died } "
            "BIND(COALESCE(?dis, ?died) AS ?ended) "
            "OPTIONAL { ?item wdt:P17 ?country } }"
        )
        req = urllib.request.Request(
            f"{SPARQL}?{urllib.parse.urlencode({'query': query, 'format': 'json'})}",
            headers={"User-Agent": UA, "Accept": "application/sparql-results+json"},
        )
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.load(r)
        for b in data["results"]["bindings"]:
            qid = b["item"]["value"].rsplit("/", 1)[-1]
            rec = out.setdefault(qid, {"defunct": False, "countries": set()})
            if b.get("ended"):
                rec["defunct"] = True
            if b.get("country"):
                rec["countries"].add(b["country"]["value"].rsplit("/", 1)[-1])
    return out


if __name__ == "__main__":
    # 1. The index reproduces a hand-written alias row from evidence alone.
    qid = search("Bharatiya Janata Party", limit=1)[0]
    keys = {alias_key(n) for n in fetch_aliases([qid])[qid]["forms"]}
    assert {"bjp", "bharatiya-janata-party"} <= keys, "the hand-list fold is not derivable"
    assert "भारतीय-जनता-पार्टी" in keys, "native script did not fold — check slugify"

    # 2. Sitelink titles are load-bearing, not belt-and-braces. Q1058 (Modi) has
    #    137 labels and NO English one; without the enwiki title the most
    #    prominent entity in the corpus is unlinkable.
    modi = fetch_aliases(["Q1058"])["Q1058"]
    assert "narendra-modi" in {alias_key(n) for n in modi["forms"]}, "sitelink title path broken"

    # 3. The case this module was built for: search cannot find the variant, and
    #    the enwiki title recovers it. If this breaks, the sitelink path is dead
    #    and the docstring's central claim is false.
    assert not search("Pakistan Muslim League-Nawaz"), "search now finds it — recheck the premise"
    plm = fetch_aliases(["Q799577"])["Q799577"]
    assert alias_key("Pakistan Muslim League-Nawaz") in {alias_key(n) for n in plm["forms"]}, \
        "the fold this module exists for is broken"

    # 4. Type filter: a journal is never a valid link for a political party.
    agents = agent_qids(["Q10230", "Q919631", "Q5"])
    assert "Q10230" in agents and "Q919631" not in agents, f"type filter wrong: {agents}"

    # 5. Context: the INC splinter is dissolved, the sitting party is not.
    ctx = entity_context(["Q10225", "Q3523002", "Q129844", "Q17003198"])
    assert ctx["Q3523002"]["defunct"] and not ctx["Q10225"]["defunct"], ctx
    assert INDIA in ctx["Q129844"]["countries"], ctx["Q129844"]
    assert INDIA not in ctx["Q17003198"]["countries"], "the Pakistani AAP looks Indian"

    print("wikidata self-check OK — hand-list rows derived, sitelink path live, limits honest")
