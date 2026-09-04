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
    """One thing somebody SAID, attributed and quotable.

    The previous shape was `{text, contested}` — a free-text assertion with no
    speaker, no quote and no span. That cannot carry a perspectives layer: "what
    has this person said across this story" is unanswerable when the speaker is
    not a field, and a claim with no verbatim quote is a summary a reader cannot
    check.

    MISATTRIBUTION IS THE WORST FAILURE THIS PRODUCT CAN HAVE. A wrong story
    boundary shows someone an unrelated card; a wrong attribution puts words in a
    named person's mouth. So the quote is verbatim or the claim is not stored —
    enforced in enrichment/claims.py against the article text, because the model
    cannot be trusted to mark its own homework.
    """

    speaker: str = Field(description="Who said it, as named in the article")
    quote_text: str = Field(description="Their words VERBATIM from the article, not paraphrased")
    claim_text: str = Field(default="", description="One neutral sentence: what they claimed")
    target: str | None = Field(default=None, description="Who or what the claim is about")
    stance: str | None = Field(default=None, description="critical|neutral|supportive|defensive")
    said_at: str | None = Field(default=None, description="ISO date if the article states one")
    # Character offsets into articles.clean_text. The model is poor at these and
    # they are REPAIRED from quote_text rather than trusted; see verify_claims.
    quote_start: int | None = None
    quote_end: int | None = None

    @field_validator("speaker", "quote_text", mode="before")
    @classmethod
    def _clean(cls, v):
        return (v or "").strip()


class Stance(BaseModel):
    label: str = Field(description="critical|neutral|supportive|defensive|alarmist|other")
    toward: str | None = Field(default=None, description="Who/what the stance is toward")


class ExtractedImpact(BaseModel):
    entity: str
    effect: str = Field(default="affected", description="e.g. service_outage, data_exposed, patch_required, stock_drop")
    direction: str = Field(default="mixed", description="positive|negative|mixed")
    horizon: str = Field(default="days", description="immediate|days|weeks|longer")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @model_validator(mode="before")
    @classmethod
    def _synonym_keys(cls, data):
        # Models drift to who/what phrasing for the affected-party fields.
        if isinstance(data, dict):
            if "entity" not in data and "who" in data:
                data["entity"] = data.pop("who")
            if "effect" not in data and "what" in data:
                data["effect"] = data.pop("what")
        return data


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
    # The description travels into the JSON schema the model is given, so it is
    # the last place to say this before the output exists. Measured in production:
    # this field collected the lens's own FIELD NAMES (`PRICE_IMPACT`, `SECTOR`,
    # `CATALYST`), values belonging to its neighbours (`MIXED`, `0.5`), company
    # nicknames (`HUL`, `BOB`, `CITI`) and three entire refusal sentences.
    tickers: list[str] = Field(
        default_factory=list,
        description=(
            "Exchange ticker symbols exactly as listed, e.g. NVDA or HINDUNILVR. "
            "Not nicknames, not indices, not field names, not explanations. "
            "Return [] when the exact symbol is unknown — [] is a correct answer."
        ),
    )
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
