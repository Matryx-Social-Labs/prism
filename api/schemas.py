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
    last_updated_at: str
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
    thread: dict  # {"upstream": [...], "downstream": [...]} of linked events
    related: list[dict] = []  # story branches — events sharing >=2 entities [{id,title,last_updated_at,shared}]
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
