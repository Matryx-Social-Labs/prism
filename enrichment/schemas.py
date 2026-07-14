"""Enrichment extraction schemas — shared fields + cyber lens.

Schema-constrained per ENRICHMENT-SCHEMA.md: fields the article does not
evidence are explicit nulls/empty, so unknown and absent are never conflated.

Validators coerce the shape-slips cloud models actually produce (schema in
prompt, not enforced server-side — see common/llm.py): flattened nesting,
strings where objects belong, nulls where lists belong. Load-bearing content
still fails loudly; only recoverable shape drift is repaired.
"""

from pydantic import BaseModel, Field, field_validator, model_validator

CYBER_EVENT_TYPES = [
    "data_breach",
    "ransomware_attack",
    "vulnerability_disclosure",
    "exploitation_activity",
    "security_advisory",
    "supply_chain_attack",
    "ddos_attack",
    "espionage_campaign",
    "security_policy",
    "other",
]


class ExtractedEntity(BaseModel):
    name: str
    type: str = Field(default="organization", description="person|company|organization|government|place|product|ticker")
    role: str = Field(default="affected", description="subject|affected|actor|source_cited")


class Claim(BaseModel):
    text: str
    contested: bool = False


class Stance(BaseModel):
    label: str = Field(description="critical|neutral|supportive|defensive|alarmist|other")
    toward: str | None = Field(default=None, description="Who/what the stance is toward")


class ExtractedImpact(BaseModel):
    entity: str
    effect: str = Field(default="affected", description="e.g. service_outage, data_exposed, patch_required, stock_drop")
    direction: str = Field(default="mixed", description="positive|negative|mixed")
    horizon: str = Field(default="days", description="immediate|days|weeks|longer")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class SharedExtraction(BaseModel):
    event_type: str = Field(default="other", description=f"One of: {', '.join(CYBER_EVENT_TYPES)}")
    headline_summary: str = Field(description="One neutral sentence")
    occurred_at: str | None = Field(default=None, description="ISO date the event occurred, null if not stated")
    entities: list[ExtractedEntity] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list, description="ISO country codes involved")
    stance: Stance | None = None
    claims: list[Claim] = Field(default_factory=list)
    impacts: list[ExtractedImpact] = Field(default_factory=list)
    sentiment: float | None = Field(default=None, ge=-1.0, le=1.0)

    @field_validator("entities", "regions", "claims", "impacts", mode="before")
    @classmethod
    def _none_to_list(cls, v):
        return v or []

    @field_validator("entities", mode="before")
    @classmethod
    def _coerce_entities(cls, v):
        if not v:
            return []
        return [{"name": e, "type": "organization", "role": "affected"} if isinstance(e, str) else e for e in v]

    @field_validator("claims", mode="before")
    @classmethod
    def _coerce_claims(cls, v):
        if not v:
            return []
        return [{"text": c} if isinstance(c, str) else c for c in v]

    @field_validator("stance", mode="before")
    @classmethod
    def _coerce_stance(cls, v):
        if isinstance(v, str):
            return {"label": v}
        if isinstance(v, dict) and "label" not in v:
            return None
        return v

    @field_validator("occurred_at", mode="before")
    @classmethod
    def _date_only(cls, v):
        return v[:10] if isinstance(v, str) and len(v) >= 10 else v


class Cvss(BaseModel):
    score: float | None = None
    vector: str | None = None
    severity: str | None = None


class AffectedProduct(BaseModel):
    vendor: str | None = None
    product: str | None = None
    versions: str | None = None


class Exploitation(BaseModel):
    known_exploited: bool | None = None
    kev_listed: bool | None = None
    poc_public: bool | None = None


class Remediation(BaseModel):
    fix_available: bool | None = None
    action: str | None = None
    workaround: str | None = None

    @field_validator("action", "workaround", mode="before")
    @classmethod
    def _join_lists(cls, v):
        if isinstance(v, list):
            return "; ".join(str(item) for item in v)
        return v


class ControlMapping(BaseModel):
    framework: str = Field(default="", description="NIST_800-53|CIS|ISO_27001")
    control: str = ""
    relevance: str = ""

    @model_validator(mode="before")
    @classmethod
    def _split_framework_from_control(cls, data):
        # Models sometimes pack "NIST_800-53 AC-3" into control with no framework.
        if isinstance(data, dict) and not data.get("framework"):
            control = str(data.get("control", ""))
            for fw in ("NIST_800-53", "CIS", "ISO_27001"):
                if control.startswith(fw):
                    data["framework"] = fw
                    data["control"] = control[len(fw):].strip(" :-")
                    break
        return data


class CyberLens(BaseModel):
    cve_ids: list[str] = Field(default_factory=list)
    cvss: Cvss | None = None
    affected: list[AffectedProduct] = Field(default_factory=list)
    exploitation: Exploitation | None = None
    weakness: list[str] = Field(default_factory=list, description="CWE ids")
    remediation: Remediation | None = None
    control_mapping: list[ControlMapping] = Field(default_factory=list)

    @field_validator("cve_ids", "weakness", "affected", "control_mapping", mode="before")
    @classmethod
    def _none_to_list(cls, v):
        return v or []

    @field_validator("affected", mode="before")
    @classmethod
    def _coerce_affected(cls, v):
        if not v:
            return []
        return [{"product": a} if isinstance(a, str) else a for a in v]

    @field_validator("exploitation", mode="before")
    @classmethod
    def _coerce_exploitation(cls, v):
        # Models sometimes return a bare status string instead of the object.
        if isinstance(v, str):
            s = v.lower()
            return {
                "known_exploited": True if ("exploit" in s or "known" in s or "active" in s) else None,
                "kev_listed": True if "kev" in s else None,
                "poc_public": True if ("poc" in s or "proof" in s) else None,
            }
        return v

    @field_validator("cvss", mode="before")
    @classmethod
    def _coerce_cvss(cls, v):
        if isinstance(v, int | float):
            return {"score": float(v)}
        return v

    @field_validator("remediation", mode="before")
    @classmethod
    def _coerce_remediation(cls, v):
        if isinstance(v, str):
            return {"action": v}
        if isinstance(v, list):
            return {"action": "; ".join(str(item) for item in v)}
        return v


class PriceImpact(BaseModel):
    direction: str | None = Field(default=None, description="up|down|mixed")
    magnitude: str | None = Field(default=None, description="minor|moderate|major")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class FinanceLens(BaseModel):
    tickers: list[str] = Field(default_factory=list, description="Ticker symbols, e.g. NVDA")
    sector: str | None = Field(default=None, description="e.g. semiconductors, banking")
    catalyst: str | None = Field(
        default=None,
        description="snake_case driver, e.g. earnings_beat, guidance_raise, rate_decision, merger, lawsuit",
    )
    price_impact: PriceImpact | None = None

    @field_validator("tickers", mode="before")
    @classmethod
    def _none_to_list(cls, v):
        return v or []

    @field_validator("price_impact", mode="before")
    @classmethod
    def _coerce_price_impact(cls, v):
        if isinstance(v, str):
            return {"direction": v}
        return v


class ArticleExtraction(BaseModel):
    """One extraction call returns shared fields plus any active lens fields."""

    shared: SharedExtraction
    cyber: CyberLens | None = None
    finance: FinanceLens | None = None

    @model_validator(mode="before")
    @classmethod
    def _hoist_flat_shape(cls, data):
        # Models often flatten the nesting, returning shared fields at top
        # level with optional lens keys. Hoist that back into shape.
        if isinstance(data, dict) and "shared" not in data and "headline_summary" in data:
            cyber = data.pop("cyber", None)
            finance = data.pop("finance", None)
            return {"shared": data, "cyber": cyber, "finance": finance}
        return data
