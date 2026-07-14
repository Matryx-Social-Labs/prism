# correlation/

Event clustering plus the perspective and impact graph. Consumes `enriched.items`, merges the many
reports of one real event into a canonical event with a persisted match trail (ported from
EduThreat canonicalization), then adds two layers: perspective grouping (cluster the event's
sources by stance and by country or party of origin, for the both-sides view) and impact
propagation (link the event to affected entities and second-order consequences without merging
identity or inflating impact). Emits `events` and `event.updates`.

See [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) and [../docs/DB-SCHEMA.md](../docs/DB-SCHEMA.md).
