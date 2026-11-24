# Names one workspace owns. Sourced by workspace_setup.sh and
# workspace_archive.sh after they cd to their own checkout; not run on its own.
#
# The name is the checkout's directory, never CONDUCTOR_WORKSPACE_NAME: that
# variable belongs to whichever shell calls the script, so running another
# workspace's script from this one would set up, or drop, the caller's databases.

ws=$(basename "$PWD" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/_/g')
case "$ws" in "" | test | *_test)  # prism_<ws> would be another workspace's test database
  echo "cannot name databases after this directory: '$ws' (empty, or ends in 'test')" >&2
  return 1 ;;
esac
db="prism_$ws"
test_db="prism_${ws}_test"
if [ ${#test_db} -gt 63 ]; then  # Postgres would silently truncate the name
  echo "directory name too long for a database name: $test_db" >&2
  return 1
fi
redis_container="prism-redis-$ws"
main="${CONDUCTOR_ROOT_PATH:-$(git worktree list | head -1 | awk '{print $1}')}"
pg_admin="prism:prism@localhost:5432"
