#!/usr/bin/env bash
# Prepare this workspace: .env, Postgres, its own Redis, venv, node_modules,
# its own two databases, migrations. Safe to run again.
set -euo pipefail
cd "$(dirname "$0")/.."
. scripts/workspace_names.sh

begin='# >>> workspace block >>>'
end='# <<< workspace block <<<'

if [ ! -f .env ]; then
  if [ -f "$main/.env" ]; then cp "$main/.env" .env; echo "env: copied $main/.env"
  else cp .env.example .env; echo "env: copied .env.example"; fi
else
  echo "env: kept existing .env"
fi

if (exec 3<>/dev/tcp/127.0.0.1/5432) 2>/dev/null; then
  echo "postgres: using what listens on 5432"
else
  echo "postgres: starting the compose postgres"
  docker compose -p prism -f "$main/docker-compose.yml" up -d --wait postgres
fi

if docker container inspect "$redis_container" >/dev/null 2>&1; then
  docker start "$redis_container" >/dev/null
else
  docker run -d --name "$redis_container" --restart unless-stopped \
    -p "127.0.0.1:${CONDUCTOR_PORT:+$((CONDUCTOR_PORT + 9))}:6379" redis:7-alpine >/dev/null
fi
redis_port=$(docker port "$redis_container" 6379/tcp | head -1 | sed 's/.*://')
echo "redis: $redis_container on port $redis_port"

if ! .venv/bin/python -c '' 2>/dev/null; then
  uv venv --clear --python 3.13
fi
uv sync --frozen
echo "python: venv synced"

if [ ! -d web/node_modules ]; then
  (cd web && npm ci --no-audit --no-fund)
fi
echo "web: node_modules present"

PG_ADMIN="$pg_admin" .venv/bin/python - "$db" "$test_db" <<'PY'
import asyncio, os, sys

import asyncpg


async def main() -> None:
    for _ in range(30):
        try:
            conn = await asyncpg.connect(f"postgresql://{os.environ['PG_ADMIN']}/postgres")
            break
        except Exception as exc:  # starting up, refusing, resetting
            last = exc
            await asyncio.sleep(1)
    else:
        sys.exit(f"postgres did not accept connections in 30 s: {last}")
    for name in sys.argv[1:]:
        if await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", name):
            print(f"databases: {name} exists")
        else:
            await conn.execute(f'CREATE DATABASE "{name}"')
            print(f"databases: created {name}")
    await conn.close()


asyncio.run(main())
PY

db_url="postgresql+asyncpg://$pg_admin/$db"
test_db_url="postgresql+asyncpg://$pg_admin/$test_db"
# Rewritten where it stands (appended the first time), so a line a task adds
# below the block stays below it and keeps winning.
above=$(sed "/^$begin\$/,\$d" .env)
below=$(sed "1,/^$end\$/d" .env)
{
  printf '%s\n' "$above"
  echo "$begin"
  echo "# Regenerated on every run of scripts/workspace_setup.sh. This workspace cannot"
  echo "# spend money: the model and X keys are blank and tracing is off. A task that"
  echo "# needs live model calls adds its key on a line BELOW this block."
  echo "DATABASE_URL=$db_url"
  echo "TEST_DATABASE_URL=$test_db_url"
  echo "REDIS_URL=redis://localhost:$redis_port/0"
  grep -E '^PRISM_EMBED_(MODEL|DIM)=' .env.example
  echo "OPENROUTER_API_KEY="
  echo "OLLAMA_API_KEY="
  echo "X_BEARER_TOKEN="
  echo "PRISM_LANGFUSE_ENABLED=false"
  echo "PRISM_EMAIL_PROVIDER=console"
  echo "$end"
  [ -z "$below" ] || printf '%s\n' "$below"
} > .env.tmp && mv .env.tmp .env
echo "env: workspace block written"

for url in "$db_url" "$test_db_url"; do
  DATABASE_URL="$url" .venv/bin/alembic upgrade head
done
echo "migrations: both databases at head"

echo
echo "  databases: $db, $test_db"
echo "  redis:     localhost:$redis_port ($redis_container)"
echo "  next:      make check"
