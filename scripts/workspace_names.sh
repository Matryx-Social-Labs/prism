# Names one Conductor workspace owns. Sourced by workspace_setup.sh and
# workspace_archive.sh; not run on its own.

ws=$(printf '%s' "${CONDUCTOR_WORKSPACE_NAME:-$(basename "$PWD")}" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/_/g')
if [ -z "$ws" ]; then
  echo "workspace name is empty; set CONDUCTOR_WORKSPACE_NAME" >&2
  return 1
fi
case "$ws" in test | *_test)  # prism_<ws> would be another workspace's test database
  echo "a workspace name may not end in 'test': $ws" >&2
  return 1 ;;
esac
db="prism_$ws"
test_db="prism_${ws}_test"
if [ ${#test_db} -gt 63 ]; then  # Postgres would silently truncate the name
  echo "workspace name too long for a database name: $test_db" >&2
  return 1
fi
redis_container="prism-redis-$ws"
main="${CONDUCTOR_ROOT_PATH:-$(git worktree list | head -1 | awk '{print $1}')}"
pg_admin="prism:prism@localhost:5432"
