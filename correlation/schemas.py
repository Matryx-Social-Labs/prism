from pydantic import BaseModel, Field


class PerspectiveGroup(BaseModel):
    label: str
    stance: str | None = None
    origin_country: str | None = None
    article_ids: list[str] = Field(default_factory=list)
    summary: str


class CorrelatedImpact(BaseModel):
    entity: str
    effect: str
    direction: str = Field(description="positive|negative|mixed")
    horizon: str = Field(description="immediate|days|weeks|longer")
    confidence: float = Field(ge=0.0, le=1.0)
    parent_index: int | None = Field(
        default=None, description="0-based index of the first-order impact this follows from"
    )


class CorrelationResult(BaseModel):
    perspectives: list[PerspectiveGroup] = Field(default_factory=list)
    impacts: list[CorrelatedImpact] = Field(default_factory=list)
