"""Cross-stage message and envelope schemas.

Stream messages are thin pointers (ids); the database rows are the
authoritative payload, which keeps every stage replayable from persisted
state (ARCHITECTURE.md "provenance first" / auditable pipeline).
"""

from datetime import datetime

from pydantic import BaseModel, Field


class RawItemEnvelope(BaseModel):
    """Normalized envelope every collector produces (INGESTION-CLASSIFICATION.md)."""

    source_slug: str
    source_type: str  # news_api | cve_feed | advisory | rss | scraper
    external_id: str
    url: str | None = None
    title: str
    body: str | None = None
    language: str | None = None
    published_at: datetime | None = None
    raw: dict = Field(default_factory=dict)


class RawItemMessage(BaseModel):
    raw_item_id: str


class ClassifiedItemMessage(BaseModel):
    raw_item_id: str


class EnrichedItemMessage(BaseModel):
    raw_item_id: str
    article_id: str
    enrichment_id: str


class EventMessage(BaseModel):
    event_id: str


class EventUpdateMessage(BaseModel):
    event_id: str
