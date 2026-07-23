"""Story-graph hygiene: the roundup-title detector.

Roundup/live-blog events ("Tamil Nadu Today: …", "… LIVE:") pack many unrelated
actors into one body and bridge unrelated stories through the shared-actor graph.
threads.py excludes them (title marker AND >=8 entities). This guards the title
marker: it must catch digests/live-blogs and leave plain headlines alone. The
entity-count floor (the other half of the rule) is what keeps single-topic items
like "IndusInd Q1 Results Today:" — which match the marker but carry few entities —
in the graph; that half is validated against the live DB, not here.
"""

import re

from correlation.threads import ROUNDUP_TITLE_RE

# Postgres \y (word boundary) ≈ Python \b.
_RE = re.compile(ROUNDUP_TITLE_RE.replace(r"\y", r"\b"), re.IGNORECASE)


def test_marker_matches_digests_and_liveblogs():
    for t in [
        "Tamil Nadu Today: Ammonia gas leak toll rises to nine",
        "Asian Markets Today: South Korea's Kospi Jumps 5%",
        "US Iran war news LIVE: US strikes Iran for 11th night",
        "CJP protest LIVE: Heavy barricading across Delhi",
        "Morning Digest: top stories of the day",
        "Weekly Roundup: what you missed",
        "Market Wrap: Sensex ends lower",
    ]:
        assert _RE.search(t), t


def test_marker_ignores_plain_headlines():
    # Real single-topic stories carry no digest/LIVE marker → stay in the graph.
    for t in [
        "Congress surprised its own MPs, Centre with protest at 7 Lok Kalyan Marg",
        "Storage in Karnataka's Cauvery reservoirs stands at 52% of total capacity",
        "Trump says US has 'no interest' in Iran talks until Tehran is ready",
        "Wangchuk shifted from Safdarjung Hospital to Medanta in Gurugram",
        "CM Vijay reviews Mekedatu issue, may announce further action in 10 days",
    ]:
        assert not _RE.search(t), t
