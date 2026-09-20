"""The shows we listen to. Measured 2026-09-20 (cadence, freshness, byte-range
support): the five live English dailies. Every Hindi daily we knew of had
stopped publishing to RSS — Hindi news audio lives on YouTube and app-only
players — so v1 is English, and a Hindi source is an open search, not a gap
this list can close.

`dai` marks a host that stitches ads in per request (Spreaker served 2.57 MB
and 2.12 MB of one episode to two user agents): the player must reconcile its
file against the one we transcribed before it seeks.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ShowSpec:
    slug: str
    name: str
    publisher: str
    feed_url: str
    site_url: str
    language: str = "en"
    dai: bool = False


SHOWS: list[ShowSpec] = [
    ShowSpec("thehindu_infocus", "In Focus", "The Hindu", "https://feeds.megaphone.fm/THGU4956605070", "https://www.thehindu.com/podcast/"),
    ShowSpec("ie_3things", "3 Things", "The Indian Express", "https://www.spreaker.com/show/5008053/episodes/feed", "https://indianexpress.com/audio/", dai=True),
    ShowSpec("et_morningbrief", "The Morning Brief", "The Economic Times", "https://www.omnycontent.com/d/playlist/60b2e926-e5f8-4b90-a465-aef901163001/95fd7c59-790d-496e-bbde-aef901167fe4/8ae54763-9925-40ca-8c3d-aef901167ffb/podcast.rss", "https://economictimes.indiatimes.com/podcast"),
    ShowSpec("finshots_daily", "Finshots Daily", "Finshots", "https://anchor.fm/s/37a76020/podcast/rss", "https://finshots.in/"),
    ShowSpec("moneycontrol", "Moneycontrol Podcast", "Moneycontrol", "https://audioboom.com/channels/4937727.rss", "https://www.moneycontrol.com/podcast/"),
]

BY_SLUG = {s.slug: s for s in SHOWS}
