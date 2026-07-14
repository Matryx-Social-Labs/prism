# ingestion/

Collectors and API adapters that pull worldwide sources and publish each observation to the
`raw.items` stream. Includes Tier 1 news-event API adapters (GDELT, NewsCatcher or Event Registry),
Tier 2 domain feeds for the cyber beachhead (NVD/CVE, CISA KEV, vendor advisories), and a few Tier 3
own collectors whose logic is ported from the EduThreat scrapers. Collectors preserve observations
exactly as received and keep per-source watermarks.

See [../docs/DATA-SOURCES.md](../docs/DATA-SOURCES.md) and
[../docs/INGESTION-CLASSIFICATION.md](../docs/INGESTION-CLASSIFICATION.md).
