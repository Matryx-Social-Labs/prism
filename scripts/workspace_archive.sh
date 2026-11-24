#!/usr/bin/env bash
# Drop this workspace's two databases and remove its Redis container.
# Never blocks an archive: failures go to stderr and the exit code is 0.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 0
. scripts/workspace_names.sh || exit 0

if [ -x .venv/bin/python ]; then
  # The only names this can drop are prism_<ws> and prism_<ws>_test, built
  # from the workspace slug ([a-z0-9_] only) in workspace_names.sh.
  PG_ADMIN="$pg_admin" .venv/bin/python - "$db" "$test_db" <<'PY' \
    || echo "archive: could not drop $db and $test_db; they are left behind" >&2
import asyncio, os, sys

import asyncpg


async def main() -> None:
    conn = await asyncpg.connect(f"postgresql://{os.environ['PG_ADMIN']}/postgres", timeout=5)
    for name in sys.argv[1:]:
        await conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        print(f"archive: dropped {name}")
    await conn.close()


asyncio.run(main())
PY
else
  echo "archive: no .venv, so $db and $test_db are left behind" >&2
fi

docker rm -f "$redis_container" >/dev/null 2>&1 \
  && echo "archive: no $redis_container container remains" \
  || echo "archive: could not remove $redis_container" >&2
exit 0
