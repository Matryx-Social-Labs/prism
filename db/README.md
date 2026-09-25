# db/

Alembic migrations (`db/versions/`), written by hand — each one's docstring says why
the change exists and what was measured. The API container runs `alembic upgrade head`
before it starts serving (`Dockerfile`), so a migration ships with the deploy that
needs it; keep heavy backfills out of migrations (see
[docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) troubleshooting) and in `tools/backfill_*`.

```bash
uv run alembic upgrade head      # local
uv run alembic heads             # must be exactly one
```

Every table: [docs/DB-SCHEMA.md](../docs/DB-SCHEMA.md).
