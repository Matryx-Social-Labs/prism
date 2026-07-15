from pydantic import BaseModel, Field, field_validator


class PerspectiveGroup(BaseModel):
    label: str
    stance: str | None = None
    origin_country: str | None = None
    article_ids: list[str] = Field(default_factory=list)
    summary: str = ""


class CorrelatedImpact(BaseModel):
    entity: str
    effect: str
    direction: str = Field(default="mixed", description="positive|negative|mixed")
    horizon: str = Field(default="days", description="immediate|days|weeks|longer")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    parent_index: int | None = Field(
        default=None, description="0-based index of the first-order impact this follows from"
    )


class CorrelationResult(BaseModel):
    perspectives: list[PerspectiveGroup] = Field(default_factory=list)
    impacts: list[CorrelatedImpact] = Field(default_factory=list)


class LensBriefs(BaseModel):
    """Per-lens written analysis of one event ("through the X lens...").

    Keys match common/lenses.py slugs. None = not generated for that lens.
    """

    general: str | None = None
    cyber_grc: str | None = None
    finance_trader: str | None = None

    @field_validator("general", "cyber_grc", "finance_trader", mode="before")
    @classmethod
    def _coerce_text(cls, v):
        if isinstance(v, list):
            return " ".join(str(item) for item in v)
        if isinstance(v, dict):  # models sometimes wrap: {"text": "..."}
            return v.get("text") or v.get("brief") or None
        return v


class ThreadLinkJudgement(BaseModel):
    """One candidate's relation to the event, from the thread-link prompt."""

    index: int
    related: bool = False
    direction: str = Field(
        default="unclear",
        description="candidate_causes_event | event_causes_candidate | unclear",
    )
    rationale: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("related", mode="before")
    @classmethod
    def _coerce_bool(cls, v):
        if isinstance(v, str):
            return v.strip().lower() in ("true", "yes", "related", "1")
        return bool(v)


class ThreadLinkResult(BaseModel):
    judgements: list[ThreadLinkJudgement] = Field(default_factory=list)

    @field_validator("judgements", mode="before")
    @classmethod
    def _coerce_list(cls, v):
        if isinstance(v, dict):  # models sometimes emit {"0": {...}, "1": {...}}
            return list(v.values())
        return v or []
