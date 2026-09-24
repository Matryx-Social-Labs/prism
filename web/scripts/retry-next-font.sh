#!/usr/bin/env bash
# Run a build, retrying ONLY when next/font's Google Fonts fetch is what failed.
#
# next/font downloads each font's CSS from Google at build time and reads the
# file extension off every font URL. Now and then Google answers with a URL that
# has none (its `/l/font?kit=` form); the loader's `/\.(woff2|…)$/.exec(url)[1]`
# is then null and the build dies with "Cannot read properties of null (reading
# '1')" — nothing wrong in the code. It failed four builds on 2026-09-23, one of
# them the production deploy. Any other failure exits at once with its own status.
#
# ponytail: retry, not self-hosting. Moving the eleven families to next/font/local
# removes the network from the build entirely; do it if this still fails after
# three tries.
set -uo pipefail

TRIES=${NEXT_FONT_TRIES:-3}
WAIT=${NEXT_FONT_WAIT_S:-15}
log=$(mktemp)
status=1
for attempt in $(seq 1 "$TRIES"); do
  "$@" 2>&1 | tee "$log"
  status=${PIPESTATUS[0]}
  [ "$status" -eq 0 ] && exit 0
  grep -q 'An error occurred in `next/font`' "$log" || exit "$status"
  [ "$attempt" -lt "$TRIES" ] || break
  echo "::warning::next/font could not read Google Fonts' answer (attempt $attempt of $TRIES); retrying"
  sleep $((attempt * WAIT))
done
exit "$status"
