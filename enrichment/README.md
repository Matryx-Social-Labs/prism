# enrichment/

Schema-constrained LLM extraction with grounded NER and retrieval augmentation. Consumes
`classified.items`, produces the shared typed fields plus any active role-lens fields (the cyber
lens adds CVE, CVSS, affected products, exploitation status, and control mapping), records
field-level provenance and the raw model output, and emits `enriched.items`.

See [../docs/ENRICHMENT-SCHEMA.md](../docs/ENRICHMENT-SCHEMA.md).
