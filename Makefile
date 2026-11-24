# Prism developer commands.
#
# `make check` is the gate. It runs everything CI runs, plus two things CI does
# NOT, and it is what CI itself should invoke so the two can never disagree
# about what "green" means.
#
# There was no task runner before this; every command was a hand-typed
# `uv run ...`, which is how the CI job and the local habit drifted apart.

.PHONY: help up down check lint fmt fmt-check test test-db fresh-test-db web seed sweep score clean promote

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up:  ## Start local infra (postgres + redis). Add PROFILE=local-llm for ollama.
	docker compose $(if $(PROFILE),--profile $(PROFILE),) up -d
	@echo "waiting for postgres..."
	@until docker compose exec -T postgres pg_isready -U prism -d prism >/dev/null 2>&1; do sleep 1; done
	@echo "ready. prism + prism_test databases available on :5432"

down:  ## Stop local infra (keeps volumes)
	docker compose down

lint:  ## Lint (ruff check). Formatting is a separate, deliberate step — see fmt-check.
	uv run ruff check .

fmt-check:  ## Formatting check. NOT in `check` yet — see the note below.
	uv run ruff format --check .

fmt:  ## Apply formatting
	uv run ruff format .
	uv run ruff check --fix .

# Both DROP and recreate the test database first: one run at a time per
# checkout. With no Postgres at all, `uv run pytest -q` still skips the DB tests.
test: fresh-test-db  ## Python tests on a fresh test database
	uv run pytest -q

test-db: fresh-test-db  ## The same, and a DB test that cannot reach the database FAILS instead of skipping
	PRISM_REQUIRE_DB=1 uv run pytest -q

web:  ## Web tests + typecheck + build
	cd web && npm test && npm run lint && npx tsc --noEmit && ./scripts/retry-next-font.sh npm run build && npm run check:guides && npm run check:charts

# The workspace's test database (scripts/workspace_setup.sh writes it to .env).
# The test targets migrate and test THAT database. Exported only when set (an
# empty DATABASE_URL would reach pydantic as ""); `fresh-test-db` then refuses
# anything that is not a _test database, before alembic can touch it.
TEST_DATABASE_URL ?= $(shell sed -n 's/^TEST_DATABASE_URL=//p' .env 2>/dev/null | tail -1)
ifneq ($(TEST_DATABASE_URL),)
check test test-db fresh-test-db: export DATABASE_URL = $(TEST_DATABASE_URL)
endif

# The suite is written for CI's empty database: it leaves 165 events a run, and
# on about the fourth run against the same database tests/test_geo.py no longer
# finds the rows it seeded. Every test target starts from here instead.
fresh-test-db:  ## Drop, recreate and migrate the test database (what CI starts from)
	@case "$$DATABASE_URL" in *_test) ;; *) \
		echo "  refusing: DATABASE_URL is not a _test database (TEST_DATABASE_URL missing from .env?)."; \
		echo "  Run: bash scripts/workspace_setup.sh"; exit 1;; esac
	@test "$$(uv run alembic heads | wc -l | tr -d ' ')" = 1 \
		|| { echo "  alembic did not report exactly one head:"; uv run alembic heads; exit 1; }
	uv run python scripts/fresh_test_db.py
	uv run alembic upgrade head

# `fmt-check` is deliberately NOT part of `check`. The repo has never been
# formatted: 87 of 151 files would change. Doing that mid-rebuild would bury
# every real diff in whitespace and make review impossible. Land it as its own
# commit at a clean boundary (after Phase 0), then add fmt-check to this target.
check: lint fresh-test-db  ## THE GATE — everything CI runs, plus a typecheck CI never did
	uv run python design/gen_css.py --check
	uv run python -c "import api.main, worker.__main__, ingestion.runner, \
classification.consumer, enrichment.consumer, correlation.consumer, \
agent.rag, personalization.ranking, common.lenses"
	uv run alembic downgrade -1
	uv run alembic upgrade head
	PRISM_REQUIRE_DB=1 uv run pytest -q
	cd web && npm test && npm run lint && npx tsc --noEmit && ./scripts/retry-next-font.sh npm run build && npm run check:guides && npm run check:charts
	@echo ""
	@echo "  check: PASS"

# Fixtures go in the DEV database, never prism_test — pytest owns that one, and
# fixture rows break tests that count.
promote:  ## Ship dev to main (prod) by FAST-FORWARD — main can never lead dev
	@# WHY A FAST-FORWARD AND NOT A MERGE. Merging a dev->main PR writes a merge
	@# commit onto main that dev does not have, so main ends up AHEAD of dev by one
	@# commit per release while their trees stay identical. Sixteen of those
	@# accumulated before anyone looked. It is pure bookkeeping, but it makes
	@# "is prod behind?" unanswerable at a glance, which is the one question this
	@# branch exists to answer.
	@#
	@# A fast-forward moves the main ref onto a commit dev already has, so main is
	@# always a PREFIX of dev's history: behind or equal, never ahead, and the
	@# comparison stays readable forever.
	@git diff --quiet || { echo "  refusing: uncommitted changes"; exit 1; }
	@git fetch -q --prune origin
	@git merge-base --is-ancestor origin/main origin/dev || { 		echo "  refusing: main is NOT an ancestor of dev, so this would not fast-forward."; 		echo "  Someone committed to main directly. Reconcile before promoting."; exit 1; }
	@test -n "$$(git rev-list origin/main..origin/dev)" || { echo "  main is already up to date"; exit 0; }
	@# Prod ships what CI actually vouched for, not what happens to be on disk.
	@# (GitHub enforces this too: the ruleset on main requires the backend and web
	@# checks to be green on the pushed commit and refuses non-fast-forwards. This
	@# local check just fails faster, with a better message.)
	@gh run list --branch dev --limit 1 --json conclusion,headSha 		--jq 'if .[0].conclusion == "success" and .[0].headSha == "'"$$(git rev-parse origin/dev)"'" 			then "" else "  refusing: dev CI is not green for this exact commit" | halt_error(1) end'
	@echo "  promoting $$(git rev-list --count origin/main..origin/dev) commit(s) to main"
	git push origin origin/dev:main

seed:  ## Load the offline fixture corpus into the DEV db (no API keys, no LLM spend)
	uv run python -m tools.load_fixtures

sweep:  ## Offline story-layer sweep against the snapshot (zero LLM cost)
	uv run python -m tools.sweep_partition --cv

score:  ## Score against the gold sets. L1 is faithful on fixtures; L2 needs the full corpus.
	uv run python -m tools.score_clustering
	@echo ""
	@echo "  NOTE: score_stories (L2) is only meaningful against the FULL corpus."
	@echo "  On the fixture subset, 1/df inflates and it over-merges by construction."
	@echo "  Use: make sweep   (snapshot of production, read-only, zero LLM cost)"

clean:  ## Remove caches
	find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache
