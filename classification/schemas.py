from typing import Literal

from pydantic import BaseModel, Field, field_validator


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
    regions: list[str] = Field(
        default_factory=list,
        description=(
            "ISO 3166-1 alpha-2 country codes of the countries involved, plus the ISO 3166-2 code of each Indian "
            "state or UT the event is LOCAL to (IN-KA, IN-MH, IN-TN) as the article itself places it: a state "
            "government, a city, a district, a state election. No state code for an event of national scope — "
            "Parliament, the Union government, the Supreme Court, RBI, a national policy — even when it is "
            "datelined New Delhi; and never a state guessed from the outlet"
        ),
    )
    language: str = "en"
    role_interests: list[str] = Field(default_factory=list)
    route: Literal["standard", "fast_lane"] = "standard"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    # Where the story sits on the subject tree (common/subjects.py), e.g.
    # "civic.crime.violent". `sector`/`subsector` above are derived from it and
    # stay for every reader that has not moved to paths.
    subject_path: str | None = None
    subject_confidence: float | None = None

    @field_validator("regions", mode="after")
    @classmethod
    def _known_codes(cls, v: list[str]) -> list[str]:
        """Upper-case, deduped; a state code survives only if it is a real
        ISO 3166-2:IN code (the model writes IN-BLR, IN-BOM, IN-KAR)."""
        from common.regions import is_state_code

        out: list[str] = []
        for code in v:
            c = str(code).strip().upper().replace("_", "-")
            if not c or c in out:
                continue
            if "-" in c and not is_state_code(c):
                continue
            out.append(c)
        return out
