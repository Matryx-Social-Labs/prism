#!/usr/bin/env bash
# Drop this workspace's two databases and remove its Redis container.
# Never blocks an archive: failures go to stderr and the exit code is 0.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 0
. scripts/workspace_names.sh || exit 0

if [ -x .venv/bin/python ]; then
  # The only names this can drop are prism_<ws> and prism_<ws>_test, built
  # from this directory's name ([a-z0-9_] only) in workspace_names.sh.
  PG_ADMIN="$pg_admin" .venv/bin/python - "$db" "$test_db" <<'PY'
import asyncio, os, sys

import asyncpg


async def main() -> None:
    try:
        conn = await asyncpg.connect(f"postgresql://{os.environ['PG_ADMIN']}/postgres", timeout=5)
    except Exception as exc:
        sys.exit(f"archive: postgres unreachable ({exc!r}); left behind: {', '.join(sys.argv[1:])}")
    for name in sys.argv[1:]:
        try:
            await conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
            print(f"archive: dropped {name}")
        except Exception as exc:
            print(f"archive: could not drop {name}, left behind: {exc!r}", file=sys.stderr)
    await conn.close()


asyncio.run(main())
PY
else
  echo "archive: no .venv, so $db and $test_db are left behind" >&2
fi

# -v: redis:7-alpine declares a /data volume that would otherwise outlive it.
docker rm -fv "$redis_container" >/dev/null \
  && echo "archive: no $redis_container container remains" \
  || echo "archive: could not remove $redis_container" >&2
exit 0
