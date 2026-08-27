-- tests/conftest.py accepts a database whose name ends in `_test` as a safe
-- target, but nothing ever created one — so `uv run pytest` has been running
-- destructively against the dev database. Those tests INSERT events, publish
-- partition runs, and supersede the current run, which detaches every live
-- storyline. Creating it here means the safe path exists by default.
SELECT 'CREATE DATABASE prism_test OWNER prism'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'prism_test')\gexec
