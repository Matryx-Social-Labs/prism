"""Deterministic cyber-lens enrichment for structured CVE records.

When the raw item IS a CVE record (NVD/KEV), the lens fields come straight
from the structured payload — no LLM needed, and provenance is exact.
Control mappings use a small static ruleset keyed on exploitation status
and fix availability (LLM-mapped for news articles instead).
"""

import html as _html
from typing import Any

from enrichment.schemas import (
    AffectedProduct,
    ArticleExtraction,
    ControlMapping,
    Cvss,
    CyberLens,
    Exploitation,
    ExtractedEntity,
    ExtractedImpact,
    Remediation,
    SharedExtraction,
)


def extract_from_nvd(cve: dict[str, Any]) -> ArticleExtraction:
    cve_id = cve.get("id", "unknown")
    # NVD ships HTML entities in descriptions, and this path never touched
    # ingestion/base.py's clean_text choke point — so 9 event summaries created
    # AFTER that fix still carried &amp;, &nbsp; and &quot;.
    #
    # unescape only, NOT clean_text: clean_text strips tags, and a CVE
    # description quotes the markup it is ABOUT — one of these summaries explains
    # that an endpoint "returns an inline <script> snippet", and stripping that
    # deletes the vulnerability. The two differ only on LITERAL markup, since
    # clean_text strips before it unescapes; for NVD's escaped entities they
    # agree. Literal is the case worth protecting, so the test uses it.
    description = _html.unescape(
        next((d["value"] for d in cve.get("descriptions", []) if d.get("lang") == "en"), "")
    )

    cvss = _best_cvss(cve.get("metrics", {}))
    affected = _affected_from_configurations(cve.get("configurations", []))
    weaknesses = sorted(
        {
            d["value"]
            for w in cve.get("weaknesses", [])
            for d in w.get("description", [])
            if d.get("value", "").startswith("CWE-")
        }
    )

    lens = CyberLens(
        cve_ids=[cve_id],
        cvss=cvss,
        affected=affected,
        exploitation=Exploitation(known_exploited=None, kev_listed=None, poc_public=None),
        weakness=weaknesses,
        remediation=Remediation(fix_available=None, action=None, workaround=None),
        control_mapping=_default_control_mapping(exploited=False),
    )

    shared = SharedExtraction(
        event_type="vulnerability_disclosure",
        headline_summary=f"{cve_id} disclosed: {description[:200]}" if description else f"{cve_id} disclosed.",
        occurred_at=(cve.get("published") or "")[:10] or None,
        entities=[
            ExtractedEntity(name=a.vendor, type="company", role="affected")
            for a in affected
            if a.vendor
        ][:5],
        regions=[],
        stance=None,
        claims=[],
        impacts=[
            ExtractedImpact(
                entity=a.product or a.vendor or "affected systems",
                effect="patch_required",
                direction="negative",
                horizon="immediate" if (cvss and (cvss.score or 0) >= 9) else "days",
                confidence=0.9,
            )
            for a in affected[:3]
        ],
        sentiment=None,
    )
    return ArticleExtraction(shared=shared, cyber=lens)


def extract_from_kev(vuln: dict[str, Any]) -> ArticleExtraction:
    cve_id = vuln.get("cveID", "unknown")
    vendor = vuln.get("vendorProject")
    product = vuln.get("product")
    ransomware = str(vuln.get("knownRansomwareCampaignUse", "")).lower() == "known"

    lens = CyberLens(
        cve_ids=[cve_id],
        cvss=None,  # KEV doesn't carry CVSS; NVD record does
        affected=[AffectedProduct(vendor=vendor, product=product, versions=None)],
        exploitation=Exploitation(known_exploited=True, kev_listed=True, poc_public=None),
        weakness=[c for c in vuln.get("cwes", []) if isinstance(c, str)],
        remediation=Remediation(
            fix_available=True if vuln.get("requiredAction") else None,
            action=vuln.get("requiredAction"),
            workaround=None,
        ),
        control_mapping=_default_control_mapping(exploited=True, ransomware=ransomware),
    )

    shared = SharedExtraction(
        event_type="exploitation_activity",
        headline_summary=(
            f"{cve_id} in {vendor} {product} is being actively exploited"
            + (" including in ransomware campaigns" if ransomware else "")
            + "."
        ),
        occurred_at=vuln.get("dateAdded"),
        entities=[
            ExtractedEntity(name=vendor, type="company", role="affected") if vendor else None,
            ExtractedEntity(name=product, type="product", role="affected") if product else None,
        ],
        regions=[],
        stance=None,
        claims=[],
        impacts=[
            ExtractedImpact(
                entity=f"{vendor} {product}".strip() or "affected systems",
                effect="active_exploitation",
                direction="negative",
                horizon="immediate",
                confidence=0.95,
            )
        ],
        sentiment=None,
    )
    shared.entities = [e for e in shared.entities if e is not None]
    return ArticleExtraction(shared=shared, cyber=lens)


def _best_cvss(metrics: dict) -> Cvss | None:
    for key in ("cvssMetricV31", "cvssMetricV40", "cvssMetricV30", "cvssMetricV2"):
        entries = metrics.get(key) or []
        if entries:
            data = entries[0].get("cvssData", {})
            return Cvss(
                score=data.get("baseScore"),
                vector=data.get("vectorString"),
                severity=(data.get("baseSeverity") or entries[0].get("baseSeverity") or "").lower()
                or None,
            )
    return None


def _affected_from_configurations(configurations: list) -> list[AffectedProduct]:
    out: list[AffectedProduct] = []
    seen: set[tuple] = set()
    for config in configurations:
        for node in config.get("nodes", []):
            for match in node.get("cpeMatch", []):
                if not match.get("vulnerable"):
                    continue
                parts = (match.get("criteria") or "").split(":")
                # cpe:2.3:part:vendor:product:version:...
                if len(parts) < 6:
                    continue
                vendor, product, version = parts[3], parts[4], parts[5]
                versions = None
                if match.get("versionStartIncluding") or match.get("versionEndExcluding"):
                    versions = (
                        f"{match.get('versionStartIncluding', '')}–{match.get('versionEndExcluding', '')}"
                    )
                elif version not in ("*", "-"):
                    versions = version
                key = (vendor, product)
                if key in seen:
                    continue
                seen.add(key)
                out.append(
                    AffectedProduct(
                        vendor=vendor.replace("_", " ").title(),
                        product=product.replace("_", " "),
                        versions=versions,
                    )
                )
    return out[:10]


def _default_control_mapping(*, exploited: bool, ransomware: bool = False) -> list[ControlMapping]:
    mappings = [
        ControlMapping(
            framework="NIST_800-53",
            control="SI-2",
            relevance="Flaw remediation — patch management applies to this vulnerability",
        ),
        ControlMapping(
            framework="CIS",
            control="7.4",
            relevance="Continuous vulnerability remediation process should pick this up",
        ),
    ]
    if exploited:
        mappings.append(
            ControlMapping(
                framework="NIST_800-53",
                control="RA-5",
                relevance="Actively exploited — prioritize in vulnerability scanning and response",
            )
        )
    if ransomware:
        mappings.append(
            ControlMapping(
                framework="CIS",
                control="11.1",
                relevance="Used in ransomware campaigns — verify data recovery capability",
            )
        )
    return mappings
