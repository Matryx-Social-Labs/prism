"""Response/request models for the serving layer.

Split out of api/main.py so route modules (api/routes/*) share one schema
source and main.py only wires the app. Pure Pydantic — no DB or app deps.
"""

from pydantic import BaseModel, Field


class CoverageOut(BaseModel):
    origins: dict[str, int]
    unknown: int = 0
    single_origin: bool = False


class OutletRef(BaseModel):
    """One registered source behind a story, as the reader sees it: a short code
    for the monogram and its place on the coverage bar (common/outlets.py)."""

    slug: str
    publisher: str
    name: str
    code: str
    origin: str  # national | intl | regional | wire
    language: str | None = None
    domain: str | None = None  # the outlet's site, for its favicon


class FeedItem(BaseModel):
    id: str
    title: str
    headline_lang: str | None = None  # language of `title`; frontend tags non-primary
    available_languages: list[str] = []  # languages this story is covered in
    summary: str | None
    sector: str | None
    subsector: str | None
    regions: list[str]
    image_url: str | None
    # The outlet whose photograph `image_url` is, for the credit on the thumbnail.
    image_outlet: OutletRef | None = None
    is_regional: bool  # profile region appears in the event's regions
    coverage: CoverageOut | None = None
    clip_shows: list[str] = []  # podcast shows with a clip on this story (slugs), ≤ 3
    event_type: str | None
    source_count: int
    cvss_score: float | None
    cvss_severity: str | None
    kev_listed: bool
    cve_ids: list[str]
    tickers: list[str]
    catalyst: str | None
    price_impact_direction: str | None
    last_updated_at: str  # when Prism last touched it — NOT when the news happened
    # The newest member article's publication time. The dateline must print
    # this, not last_updated_at, which is set to now() on every projection
    # rebuild and so showed one identical batch timestamp against every story.
    latest_published_at: str | None = None
    score: float
    # Every registered source behind the story (one per feed slug in the
    # projection); the row's coverage bar and monogram stack are drawn from it.
    outlets: list[OutletRef] = []


class FeedResponse(BaseModel):
    items: list[FeedItem]
    lens: str


class LensOut(BaseModel):
    slug: str
    name: str
    tagline: str


class LensesResponse(BaseModel):
    lenses: list[LensOut]
    default: str


class SubsectorOut(BaseModel):
    slug: str
    name: str


class SectorOut(BaseModel):
    slug: str
    name: str
    subsectors: list[SubsectorOut]


class TaxonomyResponse(BaseModel):
    sectors: list[SectorOut]


class ClipShow(BaseModel):
    slug: str
    name: str
    publisher: str
    art_url: str | None = None
    site_url: str | None = None


class ClipOut(BaseModel):
    """A stretch of a news podcast that discussed this story: the publisher's own
    audio (never ours), the transcript of just that stretch, and what the
    player needs to seek there — including the duration WE transcribed, so it
    can reconcile a file the host served with different ads stitched in."""

    show: ClipShow
    episode_title: str
    episode_url: str | None
    audio_url: str
    audio_duration_s: float | None
    published_at: str
    start_s: float
    end_s: float
    text: str
    words: list[list] = []  # [word, start_s, end_s]
    score: float


class SourceRef(BaseModel):
    article_id: str
    source_name: str
    source_slug: str
    url: str | None
    title: str
    published_at: str | None
    stance: str | None
    funding: str | None = None  # "state" | "public" | None — outlet transparency chip
    code: str | None = None  # monogram, from common/outlets.py
    origin: str | None = None  # national | intl | regional | wire
    language: str | None = None
    publisher: str | None = None  # the masthead: The Hindu's state feeds share one
    domain: str | None = None
    # The report's own lead image, as the outlet published it. Shown only as a
    # credited link preview to that article (DESIGN.md § Images), never as ours.
    image_url: str | None = None
    image_phash: str | None = None  # 64-bit dHash of the photo, hex; the rail drops near-identical ones


class PerspectiveOut(BaseModel):
    label: str
    stance: str | None
    origin_country: str | None
    summary: str | None
    article_ids: list[str]


class ImpactOut(BaseModel):
    id: str
    entity_name: str | None
    effect: str
    direction: str | None
    horizon: str | None
    confidence: float | None
    parent_impact_id: str | None


class EntityOut(BaseModel):
    name: str
    entity_type: str
    role: str


class ClaimOut(BaseModel):
    """One thing somebody said, as the article said it.

    VERIFIED FIELDS ONLY. quote_text is checked verbatim against the article at
    write time (enrichment/claims.py); the offsets are repaired from it rather
    than trusted; source and published_at come from raw_items. The extractor
    also emits `stance` and `said_at`, and they are NOT here: they are model
    opinions verify_claims never checks, and putting a guess on the same line as
    a verified quote lends the guess the quote's credibility. That credibility
    is the whole point of the section.
    """

    quote_text: str
    quote_start: int | None
    quote_end: int | None
    # The words around the quote in the article's own text, so a reader can see
    # it in place without leaving; empty when the span could not be re-verified.
    context_before: str = ""
    context_after: str = ""
    article_id: str
    source_name: str
    url: str | None
    published_at: str | None


class SpeakerClaims(BaseModel):
    speaker: str
    # Who they are, as the articles put it ("Vice President of the United
    # States"): the most-repeated non-empty role across the speaker's claims.
    role: str | None = None
    claims: list[ClaimOut]


class EventDetail(BaseModel):
    id: str
    title: str
    # Whose words the title holds: "prism" when written from the reports,
    # None when it is the first report's own headline.
    headline_by: str | None = None
    summary: str | None
    sector: str | None
    subsector: str | None
    image_url: str | None
    regions: list[str]
    occurred_at: str | None
    last_updated_at: str
    projection: dict | None
    lens_briefs: dict[str, str]
    lens_points: dict[str, list[str]]
    available_lenses: list[str]
    coverage: CoverageOut | None
    entities: list[EntityOut]
    # No story timeline here. GET /trending/{slug} owns the arc and builds it from
    # the story's FROZEN member_event_ids; this route would have built the same arc
    # from the LIVE partition, so the two could disagree about which developments
    # exist. One owner, no divergence. thread/related went with it — the timeline
    # superseded them and nothing ever read them.
    #
    # What the ticket DOES carry is the way to that owner: the slug of the
    # canonical story this event belongs to, so the story page can fetch the
    # route from /trending/{slug} — the same arc the share page shows. None when
    # no story holds the event.
    story_slug: str | None = None
    sources: list[SourceRef]
    perspectives: list[PerspectiveOut]
    impacts: list[ImpactOut]
    # READER-TIER. Claims are evidence, not lens depth: the paid tier is the
    # reading of the story, the verbatim record of who said what is free. Grouped
    # by speaker STRING because within one event the name is consistent enough
    # (measured: 3% of events carry one person under two strings, all
    # punctuation variants); folding across a story is the QID ledger's job.
    claims: list[SpeakerClaims]
    # READER-TIER too, for the same reason: what the news podcasts said about
    # this story, in their own words, is evidence. Empty unless the pipeline is
    # on and the gold_clips gate has been passed.
    clips: list[ClipOut] = []


class BriefResponse(BaseModel):
    lens: str
    brief: str | None
    points: list[str] = []
    cached: bool


class QuestionsResponse(BaseModel):
    questions: list[str]


class MoverOut(BaseModel):
    ticker: str
    note: str = ""


class DigestResponse(BaseModel):
    headline: str
    narrative: str = ""
    movers: list[MoverOut] = []
    event_ids: list[str] = []
    generated_at: str | None = None
    # The stories the digest was written from, as chart rows (the record
    # under the reading); empty when the ids no longer resolve.
    stories: list[FeedItem] = []


class AskRequest(BaseModel):
    question: str = Field(max_length=500)  # bounds the input tokens; a real question fits
    session_id: str | None = None


# --- trending -----------------------------------------------------------------
# These two routes served bare dicts until now: the only description of their
# shape lived in web/src/lib/api.ts, so the client and the server could disagree
# and nothing would say so. StoryTimeline and BranchTree — the two most
# structural screens — are the consumers.
#
# A response_model DROPS any field it does not declare, silently. That makes an
# incomplete model here worse than no model at all, so every field below is
# matched against both the producer (correlation/threads.py) and the TypeScript
# interface, and test_trending_contract.py asserts the served key sets exactly.


class RouteNodeOut(BaseModel):
    """One member of a story's route, enough to draw its glyph: the branch tree's
    node plus the day it happened, so the client reads it with the same routeShape
    the route page uses and the glyph is the map in miniature."""

    id: str
    parent_id: str | None
    off_spine: bool
    occurred_at: str | None


class RouteOut(BaseModel):
    root_id: str
    nodes: list[RouteNodeOut]


class StoryPhoto(BaseModel):
    """One outlet's photograph of one development, credited, for the stack on a story row."""

    url: str
    article_url: str | None = None
    outlet: OutletRef | None = None


class TrendingStoryOut(BaseModel):
    slug: str
    label: str
    # Up to four distinct photographs across the story's developments (one per
    # publisher first, placeholders out): the row's stack (DESIGN.md § Images).
    photos: list[StoryPhoto] = []
    cast: list[str] = []
    source_count: int
    velocity: int  # distinct new outlets in the last 6h
    developments: int
    sector: str | None
    hero_title: str | None
    hero_image: str | None
    hero_event_id: str | None = None
    first_seen_at: str | None = None
    last_updated_at: str | None = None
    # The route glyph's data; None when the story predates the current partition.
    route: RouteOut | None = None
    # Story boundaries remain provisional until the recent two-labeller set
    # passes its precision gate. Clients must not render chronology otherwise.
    boundary_status: str = "provisional"


class TrendingResponse(BaseModel):
    stories: list[TrendingStoryOut]


class StoryDevelopmentOut(BaseModel):
    id: str
    title: str
    sector: str | None
    occurred_at: str | None
    image_url: str | None
    is_current: bool
    # The causal note from event_links, rendered as "↳ {why}" under the
    # development it explains. 563 usable notes in production.
    why: str | None = None
    # How many outlets filed this development: the station's weight on the route map.
    source_count: int = 1


class BranchNodeOut(BaseModel):
    id: str
    parent_id: str | None
    off_spine: bool
    depth: int


class BranchShapeOut(BaseModel):
    """Counted, never summarised — the readout prints these verbatim."""

    developments: int
    branches: int
    satellites: int
    max_depth: int


class BranchTreeOut(BaseModel):
    root_id: str
    nodes: list[BranchNodeOut]
    shape: BranchShapeOut


class RelatedStoryOut(BaseModel):
    """A different story that touches this one: by a causal note the thread
    linker wrote across the boundary, or by cast the two share. Never drawn on
    the route; said beside it."""

    slug: str
    label: str
    developments: int
    source_count: int
    velocity: int
    last_updated_at: str | None
    shared_cast: list[str] = []
    causal: bool = False


class TrendingStoryDetail(BaseModel):
    slug: str
    canonical_slug: str  # if != the requested slug, the client should redirect
    label: str
    cast: list[str] = []
    sector: str | None
    source_count: int
    velocity: int
    status: str
    developments: list[StoryDevelopmentOut] = []
    timeline_cast: list[str] = []
    # None for a storyline that predates the current partition run — the client
    # falls back to the flat timeline, so null is a real value, not an error.
    branches: BranchTreeOut | None = None
    related: list[RelatedStoryOut] = []
    boundary_status: str = "provisional"
