"""Response/request models for the serving layer.

Split out of api/main.py so route modules (api/routes/*) share one schema
source and main.py only wires the app. Pure Pydantic — no DB or app deps.
"""

from pydantic import BaseModel


class CoverageOut(BaseModel):
    origins: dict[str, int]
    unknown: int = 0
    single_origin: bool = False


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
    is_regional: bool  # profile region appears in the event's regions
    coverage: CoverageOut | None = None
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


class SourceRef(BaseModel):
    article_id: str
    source_name: str
    source_slug: str
    url: str | None
    title: str
    published_at: str | None
    stance: str | None
    funding: str | None = None  # "state" | "public" | None — outlet transparency chip


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


class EventDetail(BaseModel):
    id: str
    title: str
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
    sources: list[SourceRef]
    perspectives: list[PerspectiveOut]
    impacts: list[ImpactOut]


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


class AskRequest(BaseModel):
    question: str
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


class TrendingStoryOut(BaseModel):
    slug: str
    label: str
    cast: list[str] = []
    source_count: int
    velocity: int  # distinct new outlets in the last 6h
    developments: int
    sector: str | None
    hero_title: str | None
    hero_image: str | None


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
