# db/

Database schema and migrations (Alembic or equivalent) for the PostgreSQL canonical and served
store with pgvector. The schema is additive: new role lenses add columns, JSONB keys, and dimension
rows rather than destructive rewrites, so existing data and served projections stay valid as roles
are added.

The full table design and the stream topics are in [../docs/DB-SCHEMA.md](../docs/DB-SCHEMA.md).
