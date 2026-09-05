# Prism backend image — used by both Railway services:
#   api:    uvicorn api.main:app --host 0.0.0.0 --port $PORT
#   worker: python -m worker
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependency layer (cached until pyproject/lock change)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Application code
COPY . .
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# Bake the embedding model into the image: containers have no persistent
# cache, so without this every boot re-downloads from HF (slow cold starts).
#
# The model is read from common/config.py rather than hardcoded. It WAS
# hardcoded to BAAI/bge-small-en-v1.5 (384-dim) long after the default moved to
# a 768-dim multilingual model, so the bake cached a model the app never loads
# and production re-downloaded on every boot — a cold-start optimization that
# silently did nothing. tests/test_dockerfile_bake.py fails if this drifts again.
# Loaded through the APP'S OWN loader, not fastembed directly. _get_model()
# registers models fastembed does not ship in its registry (add_custom_model),
# and mE5 is one of them — calling TextEmbedding(name) here failed the build with
# "Model intfloat/multilingual-e5-base is not supported" the first time the
# configured model was a custom one. Going through the same function production
# uses means the bake cannot bake something the app cannot load.
RUN python -c "from common.embeddings import _get_model; _get_model()"

# One image, two roles: PRISM_SERVICE_ROLE=worker runs the pipeline worker;
# anything else (default) runs migrations + the API. Lets both Railway
# services share the image with no per-service start-command override.
CMD ["sh", "-c", "if [ \"$PRISM_SERVICE_ROLE\" = \"worker\" ]; then exec python -m worker; else alembic upgrade head && exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}; fi"]
