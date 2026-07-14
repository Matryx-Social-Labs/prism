from typing import Literal

from pydantic import BaseModel, Field


class GateResult(BaseModel):
    is_relevant: bool
    reason: str = Field(description="One short sentence explaining the decision")


class ClassificationResult(BaseModel):
    sector: Literal[
        "cybersecurity",
        "finance",
        "politics",
        "business",
        "technology",
        "sports",
        "health",
        "other",
    ]
    regions: list[str] = Field(default_factory=list, description="ISO country codes involved")
    language: str = "en"
    role_interests: list[str] = Field(default_factory=list)
    route: Literal["standard", "fast_lane"] = "standard"
    confidence: float = Field(ge=0.0, le=1.0)
