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

## Lock timeout

Every migration runs with `lock_timeout` 5 s (`common.db.migration_connect_args`,
`PRISM_MIGRATION_LOCK_TIMEOUT` overrides). A migration that cannot get its lock fails
instead of queueing every reader behind its DDL: the API container's
`alembic upgrade head` exits with `LockNotAvailable`, and Railway retries the start.
Retry the deploy; if it keeps failing on a busy table, raise
`PRISM_MIGRATION_LOCK_TIMEOUT` for that deploy.

`CREATE INDEX CONCURRENTLY` is the exception. A lock timeout part-way leaves an
INVALID index that `IF NOT EXISTS` then silently skips. Inside the
`autocommit_block()`, switch the timeout off around the build:

```python
with op.get_context().autocommit_block():
    op.execute("SET lock_timeout = 0")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ...")
    op.execute("RESET lock_timeout")
```

If a build did fail, drop the invalid index (`DROP INDEX CONCURRENTLY ...`) before
retrying. `tests/test_migration_lock_timeout.py` enforces the pattern.
