"""SQLAlchemy ORM models — prototype subset of docs/DB-SCHEMA.md.

Deferred tables (users, plans, alerts, subscriptions, user_event_scores,
feed_items, role_lenses) bolt on later; the schema is additive by design.
"""

import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from common.config import get_settings

EMBED_DIM = get_settings().prism_embed_dim


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


# ── Ingestion layer ──────────────────────────────────────────────────


class Source(TimestampMixin, Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = uuid_pk()
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)  # news_api|cve_feed|advisory|rss|scraper
    country: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(Text)
    reliability: Mapped[dict | None] = mapped_column(JSONB)
    watermark: Mapped[dict | None] = mapped_column(JSONB)  # per-source incremental cursor


class RawItem(TimestampMixin, Base):
    __tablename__ = "raw_items"
    __table_args__ = (UniqueConstraint("source_id", "external_id", name="uq_raw_items_source_external"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False)  # untouched source payload
    image_url: Mapped[str | None] = mapped_column(Text)
    relevance: Mapped[str] = mapped_column(Text, default="pending", nullable=False)  # pending|relevant|rejected
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    classification: Mapped[dict | None] = mapped_column(JSONB)


class Article(TimestampMixin, Base):
    __tablename__ = "articles"

    id: Mapped[uuid.UUID] = uuid_pk()
    raw_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("raw_items.id"), nullable=False)
    clean_text: Mapped[str] = mapped_column(Text, nullable=False)
    retrieval_tier: Mapped[str] = mapped_column(Text, default="direct", nullable=False)  # direct|proxy|archive|body
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ArticleChunk(TimestampMixin, Base):
    __tablename__ = "article_chunks"
    __table_args__ = (UniqueConstraint("article_id", "chunk_index", name="uq_article_chunks_article_idx"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    article_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articles.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBED_DIM))


# ── Enrichment layer ─────────────────────────────────────────────────


class Enrichment(TimestampMixin, Base):
    __tablename__ = "enrichments"

    id: Mapped[uuid.UUID] = uuid_pk()
    article_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articles.id"), nullable=False)
    event_type: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[date | None] = mapped_column(Date)
    sentiment: Mapped[float | None] = mapped_column(Float)
    shared_fields: Mapped[dict | None] = mapped_column(JSONB)  # claims, stance, regions, entities, impacts
    lens_fields: Mapped[dict | None] = mapped_column(JSONB)  # keyed by lens, e.g. {"cyber": {...}}
    raw_model_output: Mapped[dict | None] = mapped_column(JSONB)  # for reproducibility
    model: Mapped[str | None] = mapped_column(Text)  # provider + model id, for auditability


class FieldProvenance(TimestampMixin, Base):
    __tablename__ = "field_provenance"

    id: Mapped[uuid.UUID] = uuid_pk()
    enrichment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("enrichments.id"), nullable=False)
    field_path: Mapped[str] = mapped_column(Text, nullable=False)  # e.g. impacts[0].effect
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)


# ── Canonical event layer ────────────────────────────────────────────


class Event(TimestampMixin, Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    sector: Mapped[str | None] = mapped_column(Text)
    subsector: Mapped[str | None] = mapped_column(Text)
    regions: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    image_url: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[date | None] = mapped_column(Date)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    projection: Mapped[dict | None] = mapped_column(JSONB)  # promoted shared + lens fields for serving
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBED_DIM))


class EventMembership(TimestampMixin, Base):
    __tablename__ = "event_memberships"
    __table_args__ = (UniqueConstraint("event_id", "article_id", name="uq_event_memberships_event_article"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), nullable=False)
    article_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articles.id"), nullable=False)
    match_type: Mapped[str] = mapped_column(Text, nullable=False)  # url_exact|resolved_url|title_time|entity_time|embedding|feed
    match_score: Mapped[float | None] = mapped_column(Float)
    is_survivor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class EventLink(TimestampMixin, Base):
    """Cross-event thread edge (war → markets-drop coverage, etc.).

    relation: leads_to | related | none. 'none' rows persist LLM
    rejections so a candidate pair is never re-asked.
    """

    __tablename__ = "event_links"
    __table_args__ = (UniqueConstraint("from_event_id", "to_event_id", name="uq_event_links_pair"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    from_event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    to_event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    relation: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    rationale: Mapped[str | None] = mapped_column(Text)


# ── Perspective and impact graph ─────────────────────────────────────


class Entity(TimestampMixin, Base):
    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = uuid_pk()
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)  # person|company|organization|government|place|product|ticker
    aliases: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    meta: Mapped[dict | None] = mapped_column("metadata", JSONB)


class EventEntity(TimestampMixin, Base):
    __tablename__ = "event_entities"
    __table_args__ = (
        UniqueConstraint("event_id", "entity_id", name="uq_event_entities_event_entity"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id"), nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)  # subject|affected|actor|source_cited
    provenance: Mapped[dict | None] = mapped_column(JSONB)


class Perspective(TimestampMixin, Base):
    __tablename__ = "perspectives"

    id: Mapped[uuid.UUID] = uuid_pk()
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)  # e.g. "vendor framing", "researcher framing"
    origin_country: Mapped[str | None] = mapped_column(Text)
    stance: Mapped[str | None] = mapped_column(Text)
    member_articles: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)))
    summary: Mapped[str | None] = mapped_column(Text)


class Impact(TimestampMixin, Base):
    __tablename__ = "impacts"

    id: Mapped[uuid.UUID] = uuid_pk()
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("entities.id"))
    effect: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str | None] = mapped_column(Text)  # positive|negative|mixed
    horizon: Mapped[str | None] = mapped_column(Text)  # immediate|days|weeks|longer
    confidence: Mapped[float | None] = mapped_column(Float)
    parent_impact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("impacts.id"))
    provenance: Mapped[dict | None] = mapped_column(JSONB)


# ── Agent layer ──────────────────────────────────────────────────────


class AgentSession(TimestampMixin, Base):
    __tablename__ = "agent_sessions"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_ref: Mapped[str | None] = mapped_column(Text)  # placeholder until real users exist
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AgentMessage(TimestampMixin, Base):
    __tablename__ = "agent_messages"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)  # user|assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    cited_source_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)))


# ── Product & monetization layer (freemium build) ────────────────────


class User(TimestampMixin, Base):
    """Account identity. The magic-link auth flow attaches in a later PR; this is
    the minimal stable row that quota/subscriptions reference (replaces the
    AgentSession.user_ref='default' placeholder)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    # Collected at sign-up to curate professional news lists later. profession is
    # a slug from common.professions; nullable for pre-existing rows.
    name: Mapped[str | None] = mapped_column(Text)
    profession: Mapped[str | None] = mapped_column(Text)


class UsageQuota(TimestampMixin, Base):
    """Per-account pro-lens sample cap (freemium D4/D13 — Markets-only, so one
    counter per user is enough).

    Decremented with a single atomic ``UPDATE ... WHERE remaining > 0 RETURNING``
    (see common/quota.py) so two concurrent viewers of the same event+lens can
    never double-spend the last sample. Server-side + per-account by construction;
    never device/IP, which would be farmable and reopen the unbounded-LLM-bill hole.
    """

    __tablename__ = "usage_quota"
    __table_args__ = (UniqueConstraint("user_id", name="uq_usage_quota_user"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    remaining: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuthToken(TimestampMixin, Base):
    """Single-use magic-link token. Only the SHA-256 hash is stored — the raw
    token exists only in the emailed link (N3). Consumed on first successful
    verify; expired/consumed tokens never authenticate."""

    __tablename__ = "auth_tokens"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Sign-up profile carried through the magic-link flow, applied when the token
    # creates a brand-new user.
    name: Mapped[str | None] = mapped_column(Text)
    profession: Mapped[str | None] = mapped_column(Text)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Session(TimestampMixin, Base):
    """Bearer session. The client holds the raw token; we store its SHA-256 hash.
    Bearer (not cookie) so there is no CSRF surface (N3). Revocable by deleting
    the row."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Watchlist(TimestampMixin, Base):
    """A user's followed ticker or sector — read-only follow (see their events on
    open). Push/alerts are Phase 2 (need delivery infra). One row per (user, kind,
    value); unique so following the same thing twice is a no-op."""

    __tablename__ = "watchlist"
    __table_args__ = (
        UniqueConstraint("user_id", "kind", "value", name="uq_watchlist_user_kind_value"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # ticker | sector
    value: Mapped[str] = mapped_column(Text, nullable=False)  # e.g. "SBIN" or "finance"
