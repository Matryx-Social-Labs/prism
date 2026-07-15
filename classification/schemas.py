from typing import Literal

from pydantic import BaseModel, Field


class GateResult(BaseModel):
    # Audit-only fields default: Ollama's schema-constrained decoding doesn't
    # reliably enforce `required`, and a missing reason must not fail the gate.
    is_relevant: bool
    reason: str = Field(default="", description="One short sentence explaining the decision")


class ClassificationResult(BaseModel):
    sector: Literal[
        "cybersecurity",
        "finance",
        "politics",
        "business",
        "technology",
        "sports",
        "health",
        "entertainment",
        "science",
        "other",
    ]
    # Validated against common/taxonomy.py after the LLM call — constrained
    # decoding can't express per-sector enums, so invalid values become None.
    subsector: str | None = None
    regions: list[str] = Field(default_factory=list, description="ISO country codes involved")
    language: str = "en"
    role_interests: list[str] = Field(default_factory=list)
    route: Literal["standard", "fast_lane"] = "standard"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
