"""Enrichment extraction schemas — shared fields + cyber lens.

Schema-constrained per ENRICHMENT-SCHEMA.md: fields the article does not
evidence are explicit nulls/empty, so unknown and absent are never conflated.
"""

from pydantic import BaseModel, Field

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
    type: str = Field(description="person|company|organization|government|place|product|ticker")
    role: str = Field(description="subject|affected|actor|source_cited")


class Claim(BaseModel):
    text: str
    contested: bool = False


class Stance(BaseModel):
    label: str = Field(description="critical|neutral|supportive|defensive|alarmist|other")
    toward: str | None = Field(default=None, description="Who/what the stance is toward")


class ExtractedImpact(BaseModel):
    entity: str
    effect: str = Field(description="e.g. service_outage, data_exposed, patch_required, stock_drop")
    direction: str = Field(default="mixed", description="positive|negative|mixed")
    horizon: str = Field(default="days", description="immediate|days|weeks|longer")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class SharedExtraction(BaseModel):
    event_type: str = Field(description=f"One of: {', '.join(CYBER_EVENT_TYPES)}")
    headline_summary: str = Field(description="One neutral sentence")
    occurred_at: str | None = Field(default=None, description="ISO date the event occurred, null if not stated")
    entities: list[ExtractedEntity] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list, description="ISO country codes involved")
    stance: Stance | None = None
    claims: list[Claim] = Field(default_factory=list)
    impacts: list[ExtractedImpact] = Field(default_factory=list)
    sentiment: float | None = Field(default=None, ge=-1.0, le=1.0)


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


class ControlMapping(BaseModel):
    framework: str = Field(description="NIST_800-53|CIS|ISO_27001")
    control: str
    relevance: str


class CyberLens(BaseModel):
    cve_ids: list[str] = Field(default_factory=list)
    cvss: Cvss | None = None
    affected: list[AffectedProduct] = Field(default_factory=list)
    exploitation: Exploitation | None = None
    weakness: list[str] = Field(default_factory=list, description="CWE ids")
    remediation: Remediation | None = None
    control_mapping: list[ControlMapping] = Field(default_factory=list)


class ArticleExtraction(BaseModel):
    """One extraction call returns shared fields plus the cyber lens (when active)."""

    shared: SharedExtraction
    cyber: CyberLens | None = None
