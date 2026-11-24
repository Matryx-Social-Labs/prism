#!/usr/bin/env bash
# Prepare this workspace: Postgres, its own Redis, venv, node_modules, its own
# two databases, migrations, and a .env that points at them. Safe to run again.
set -euo pipefail
trap 'echo "workspace_setup: FAILED at line $LINENO ($BASH_COMMAND). This workspace is NOT ready." >&2' ERR
cd "$(dirname "$0")/.."
. scripts/workspace_names.sh

begin='# >>> workspace block >>>'
end='# <<< workspace block <<<'

# .env is written once, at the end: a setup that fails half-way must not leave a
# copy of the main checkout's file (shared database, live keys) that looks ready.
if [ -f .env ]; then env_source=.env
elif [ -f "$main/.env" ]; then env_source="$main/.env"
else env_source=.env.example; fi
if [ "$(grep -cxF "$begin" "$env_source" || true)" != "$(grep -cxF "$end" "$env_source" || true)" ]; then
  echo "$env_source has one workspace-block marker without the other; restore the pair or delete both" >&2
  exit 1
fi
echo "env: from $env_source"

compose="docker compose -p prism -f $main/docker-compose.yml"
if (exec 3<>/dev/tcp/127.0.0.1/5432) 2>/dev/null; then
  echo "postgres: using what listens on 5432"
else
  echo "postgres: starting the compose postgres"
  # Two workspaces set up at once both get here; the loser's `up` fails on the
  # container name. The connect loop below decides whether Postgres is there.
  $compose up -d --wait postgres || true
fi
# Redis below comes back after a reboot; without this the compose Postgres would not.
pg_container=$($compose ps -aq postgres)
[ -z "$pg_container" ] || docker update --restart unless-stopped "$pg_container" >/dev/null

if docker container inspect "$redis_container" >/dev/null 2>&1; then
  docker start "$redis_container" >/dev/null
else
  # ponytail: outside Conductor (no CONDUCTOR_PORT) docker picks the port and may
  # pick another after a restart; re-run this script to refresh REDIS_URL.
  docker run -d --name "$redis_container" --restart unless-stopped \
    -p "127.0.0.1:${CONDUCTOR_PORT:+$((CONDUCTOR_PORT + 9))}:6379" redis:7-alpine >/dev/null \
    || { docker rm -fv "$redis_container" >/dev/null 2>&1; false; }  # a failed run leaves a dead container that blocks the next one
fi
redis_port=$(docker port "$redis_container" 6379/tcp | head -1 | sed 's/.*://')
echo "redis: $redis_container on port $redis_port"

# 3.13 by name: the machine's default Python (3.15) has no onnxruntime wheel.
if ! .venv/bin/python -c 'import sys; sys.exit(sys.version_info[:2] != (3, 13))' 2>/dev/null; then
  uv venv --clear --python 3.13
fi
uv sync --frozen
echo "python: venv synced"

if [ ! -f web/node_modules/.package-lock.json ]; then  # npm writes it last, so a half install is redone
  (cd web && npm ci --no-audit --no-fund)
fi
echo "web: node_modules present"

PG_ADMIN="$pg_admin" .venv/bin/python - "$db" "$test_db" <<'PY'
import asyncio, os, sys

import asyncpg


async def main() -> None:
    for _ in range(30):
        try:
            conn = await asyncpg.connect(f"postgresql://{os.environ['PG_ADMIN']}/postgres", timeout=2)
            break
        except Exception as exc:  # starting up, refusing, resetting
            last = exc
            await asyncio.sleep(1)
    else:
        sys.exit(f"postgres did not accept connections: {last!r}")
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
embed=$(grep -E '^PRISM_EMBED_(MODEL|DIM)=' .env.example)  # the values the tests expect; a stale copied .env had 384
block="$begin
# Regenerated on every run of scripts/workspace_setup.sh. These keys are set
# here and nowhere above: this file gives the workspace its own databases and
# Redis, and no model or X key. A task that needs live model calls adds its key
# on a line BELOW this block.
DATABASE_URL=$db_url
TEST_DATABASE_URL=$test_db_url
REDIS_URL=redis://localhost:$redis_port/0
$embed
OPENROUTER_API_KEY=
OLLAMA_API_KEY=
X_BEARER_TOKEN=
PRISM_LANGFUSE_ENABLED=false
PRISM_EMAIL_PROVIDER=console
$end"
# Every key the block sets is removed above it. Last-wins parsing would be
# enough for the app, but some tools read the FIRST DATABASE_URL in .env, and a
# copied live key should not sit in this file at all.
keys=$(printf '%s\n' "$block" | sed -n 's/^\([A-Z_]*\)=.*/\1/p' | paste -sd'|' -)
above=$(sed "/^$begin\$/,\$d" "$env_source" | grep -vE "^($keys)=" || true)
below=$(sed "1,/^$end\$/d" "$env_source")
if [ -f .env ] && ! grep -qxF "$begin" .env; then
  cp .env .env.before-workspace-setup
  echo "env: an existing .env is rewritten; the original is kept as .env.before-workspace-setup"
fi
{
  printf '%s\n' "$above" "$block"
  [ -z "$below" ] || printf '%s\n' "$below"
} > .env.tmp
mv .env.tmp .env
echo "env: workspace block written"
for key in OPENROUTER_API_KEY OLLAMA_API_KEY X_BEARER_TOKEN; do
  [ -z "${!key:-}" ] || echo "warning: $key is exported in this shell and overrides .env — this workspace CAN spend" >&2
done

for url in "$db_url" "$test_db_url"; do
  DATABASE_URL="$url" .venv/bin/alembic upgrade head
done
echo "migrations: both databases at head"

echo
echo "  databases: $db, $test_db"
echo "  redis:     localhost:$redis_port ($redis_container)"
echo "  next:      make check"
