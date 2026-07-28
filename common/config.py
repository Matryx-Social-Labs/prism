import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Infrastructure
    database_url: str = "postgresql+asyncpg://prism:prism@localhost:5432/prism"
    redis_url: str = "redis://localhost:6379/0"

    # LLM provider. Both are OpenAI-compatible, so switching is base_url + key +
    # model IDs. OpenRouter is primary (per-token, no weekly cap, one key for many
    # models, structured output, provider fallback). Set LLM_PROVIDER=ollama +
    # override the model IDs below to fall back to Ollama Cloud.
    llm_provider: str = "openrouter"  # openrouter | ollama
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # Ollama Cloud (fallback, OpenAI-compatible)
    ollama_api_key: str = ""
    ollama_base_url: str = "https://ollama.com/v1"

    # Per-stage models — OpenRouter IDs, every one env-overridable (PRISM_MODEL_*).
    # Confirm current IDs on openrouter.ai/models. Cheap-reliable flash-lite for the
    # high-volume structured stages (free models proved unreliable at JSON output —
    # tencent/hy3:free returned empty content), cheap-paid for the content the
    # product sells. All near-free at India-only volume.
    prism_model_gate: str = "google/gemini-3.1-flash-lite"  # binary relevance — high volume
    prism_model_classify: str = "google/gemini-3.1-flash-lite"
    # Extraction emits a nested JSON (entities/stance/cyber/finance). Entities drive
    # clustering, so the model MUST reliably fill them. Benchmarked on 25 real India
    # articles (recall vs qwen3.7-plus): gemini-3.1-flash-lite left 40% empty (recall
    # 0.39), gemini-3.5-flash 96% empty (0.08), deepseek-v4-flash 25% empty + truncation.
    # qwen3.5-flash is the cheapest that stays reliable — 0 empty, ~0.77 recall — at
    # ~4.7x lower cost than qwen3.7-plus ($0.07/$0.26 vs $0.32/$1.28 per M). Soft-news
    # (extract_light) uses it too: gemini-flash-lite was silently emitting no entities.
    prism_model_extract: str = "qwen/qwen3.5-flash-02-23"
    prism_model_extract_light: str = "qwen/qwen3.5-flash-02-23"
    prism_model_correlate: str = "qwen/qwen3.7-plus"  # analysis/briefs/digest — content quality
    prism_model_agent: str = "qwen/qwen3.7-plus"  # Ask — user-facing
    prism_model_judge: str = "google/gemini-3.5-flash"  # evals — low volume, wants strong reasoning
    prism_model_guard: str = "google/gemini-3.1-flash-lite"  # Ask moderation — cheap + fast

    # Embeddings (fastembed, in-process). Multilingual so cross-language coverage
    # (Hindi/Tamil/Telugu now, Spanish/etc. as we add countries) clusters into the
    # same story. Benchmarked on real CJP coverage: same-story sim Hindi 0.87 /
    # Telugu 0.77 / Tamil 0.56 vs unrelated -0.01 (bge-small-en couldn't separate
    # Hindi at all). Changing dim requires a migration of the vector(...) columns.
    prism_embed_model: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    prism_embed_dim: int = 768

    # Ask-agent guardrail — a cheap moderation pre-check rejects explicit/harmful
    # /off-topic/prompt-injection questions BEFORE the expensive RAG agent runs,
    # so we neither generate disallowed content nor pay for junk prompts.
    prism_ask_guard_enabled: bool = True

    # Live ingestion master switch. Set PRISM_INGESTION_ENABLED=false to stop
    # collectors (and the stalled-item requeue) so no new news is fetched and the
    # downstream LLM pipeline goes idle — the cost brake while the prototype is
    # still being built. On-demand briefs/Ask/digest still work.
    prism_ingestion_enabled: bool = True

    # Relevance gate — embedding pre-filter (freemium-lens-model PR0).
    # shadow: score every LLM-gated item with embeddings and LOG (score,
    # llm_decision) for calibration, without changing what gets filtered.
    #
    # Calibration verdict (2026-07-20, n=500 DB-labeled raw_items, balanced):
    # the embedding score does NOT separate well enough to enforce. Max-cosine-
    # to-positive-anchors AUC=0.67; contrastive (positive minus negative anchors)
    # AUC=0.72. At a safe content-loss budget (<=3% of relevant news dropped) it
    # gates only ~5% of junk — negligible. To gate ~13% of junk it drops ~5% of
    # real news, which fails the "don't degrade content" bar. So `enforce` stays
    # UNWIRED and unused: keep the LLM gate. Revisit only with a better signal
    # (logistic head on logged (embedding, llm_label) pairs, or a stronger
    # embedder) — not by flipping this flag.
    prism_gate_mode: str = "shadow"  # shadow | (enforce: not implemented — see above) | off

    # Langfuse (self-hosted). The SDK also reads LANGFUSE_* env vars directly;
    # these mirror them so app code can check whether tracing is configured.
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = ""
    # Tags every trace with an environment so local/dev traces are filterable and
    # never mixed with prod in the shared Langfuse. Local sets "development";
    # prod leaves it unset (shows as "default"), so prod config is untouched.
    langfuse_tracing_environment: str = ""
    # The SDK's 5s default OTLP-export timeout is too short for a self-hosted
    # Langfuse (web -> Redis -> worker -> ClickHouse): batches time out and get
    # dropped ("Failed to export span batch"). Give it room + smaller batches.
    langfuse_timeout: int = 30  # seconds — OTLP span-export timeout (LANGFUSE_TIMEOUT)
    langfuse_flush_at: int = 128  # max spans per export batch (LANGFUSE_FLUSH_AT)

    # API
    cors_origins: str = "http://localhost:3000"
    prism_admin_token: str = "change-me"

    # Auth (magic-link, bearer). Web URL is where the verify link points.
    prism_web_url: str = "http://localhost:3000"
    prism_email_provider: str = "console"  # console (dev) | resend
    resend_api_key: str = ""
    prism_email_from: str = "Prism <onboarding@resend.dev>"  # set to a verified domain sender
    prism_magic_token_ttl_min: int = 15  # magic-link lifetime
    prism_session_ttl_days: int = 30  # bearer session lifetime
    prism_magic_request_cooldown_s: int = 30  # per-email rate limit on link requests
    prism_free_markets_samples: int = 3  # sample grant on signup (D13 Markets-only)

    # Sources
    nvd_api_key: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    _export_langfuse_env(settings)
    return settings


def _export_langfuse_env(settings: Settings) -> None:
    """Bridge .env values to process env for the Langfuse SDK.

    pydantic-settings reads .env itself but doesn't export; the Langfuse
    client (and its openai wrapper) reads os.environ directly. Without this,
    keys in .env leave the SDK silently disabled. Existing env vars win.
    """
    if not settings.langfuse_enabled:
        return
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    if settings.langfuse_base_url:
        # v3 SDK reads LANGFUSE_HOST; some tooling reads LANGFUSE_BASE_URL — set both.
        os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_base_url)
        os.environ.setdefault("LANGFUSE_BASE_URL", settings.langfuse_base_url)
    if settings.langfuse_tracing_environment:
        os.environ.setdefault("LANGFUSE_TRACING_ENVIRONMENT", settings.langfuse_tracing_environment)
    # Longer OTLP-export timeout + smaller batches so traces reach a self-hosted
    # Langfuse instead of timing out and being dropped.
    os.environ.setdefault("LANGFUSE_TIMEOUT", str(settings.langfuse_timeout))
    os.environ.setdefault("LANGFUSE_FLUSH_AT", str(settings.langfuse_flush_at))
