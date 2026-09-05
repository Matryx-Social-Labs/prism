import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Infrastructure
    database_url: str = Field("postgresql+asyncpg://prism:prism@localhost:5432/prism", repr=False)
    redis_url: str = Field("redis://localhost:6379/0", repr=False)

    # LLM provider. Both are OpenAI-compatible, so switching is base_url + key +
    # model IDs. OpenRouter is primary (per-token, no weekly cap, one key for many
    # models, structured output, provider fallback). Set LLM_PROVIDER=ollama +
    # override the model IDs below to fall back to Ollama Cloud.
    llm_provider: str = "openrouter"  # openrouter | ollama
    openrouter_api_key: str = Field("", repr=False)
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # Ollama Cloud (fallback, OpenAI-compatible)
    ollama_api_key: str = Field("", repr=False)
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
    # MEASURED 2026-09-04 on 10 production articles, same prompt, claims enabled:
    #
    #   qwen/qwen3.5-flash-02-23      failed 10/10   0 claims    0 entities
    #   google/gemini-3.1-flash-lite  failed  0/10  16 claims   77 entities
    #   google/gemini-3.5-flash       failed  0/10  15 claims   73 entities
    #
    # qwen answers with a BARE NUMBER instead of the object — `-8.039215789473683`,
    # a stray sentiment value with no object in the response at all. It has worked
    # historically (1,095 enrichments carry its name), so this is degradation
    # rather than a mistake in choosing it, and the stream's redelivery hid the
    # cost: production still only loses 3.6% of relevant items permanently, but
    # roughly half of every extraction attempt was being paid for and thrown away.
    #
    # THIS REVERSES A RECORDED FINDING and the reversal is the point: the earlier
    # note said gemini "empties entities", which is why qwen was chosen. On this
    # sample gemini returns 77 entities and qwen returns none, because qwen
    # returns nothing at all. Re-measure before trusting either direction again.
    prism_model_extract: str = "google/gemini-3.1-flash-lite"
    prism_model_extract_light: str = "google/gemini-3.1-flash-lite"
    prism_model_correlate: str = "qwen/qwen3.7-plus"  # analysis/briefs/digest — content quality
    prism_model_agent: str = "qwen/qwen3.7-plus"  # Ask — user-facing
    prism_model_judge: str = "google/gemini-3.5-flash"  # evals — low volume, wants strong reasoning
    prism_model_guard: str = "google/gemini-3.1-flash-lite"  # Ask moderation — cheap + fast

    # Embeddings (fastembed, in-process). Multilingual so cross-language coverage
    # (Hindi/Tamil/Telugu now, Spanish/etc. as we add countries) clusters into the
    # same story. Benchmarked on real CJP coverage: same-story sim Hindi 0.87 /
    # Telugu 0.77 / Tamil 0.56 vs unrelated -0.01 (bge-small-en couldn't separate
    # Hindi at all). Changing dim requires a migration of the vector(...) columns.
    # mE5, chosen on a full cascade replay against gold_pairs rather than on the
    # isolated embedding score — measured 2026-09-05, both folds:
    #
    #                       all 398        batch1 (fitted)  batch2 (HELD OUT)
    #     mpnet             Cdet 0.5930    Cdet 0.5268      Cdet 0.6555
    #     mE5 + passage:    Cdet 0.5466    Cdet 0.5179      Cdet 0.5837
    #     mE5 + query:      Cdet 0.5319    Cdet 0.4598      Cdet 0.5949
    #
    # mE5 beats mpnet on F1 and Cdet in BOTH folds, which is what step 4 failed to
    # do. 768-dim either way, so no vector migration.
    prism_embed_model: str = "intfloat/multilingual-e5-base"
    prism_embed_dim: int = 768

    # Ask-agent guardrail — a cheap moderation pre-check rejects explicit/harmful
    # /off-topic/prompt-injection questions BEFORE the expensive RAG agent runs,
    # so we neither generate disallowed content nor pay for junk prompts.
    prism_ask_guard_enabled: bool = True

    # Live ingestion master switch. Set PRISM_INGESTION_ENABLED=false to stop
    # collectors (and the stalled-item requeue) so no new news is fetched and the
    # downstream LLM pipeline goes idle — the cost brake while the prototype is
    # still being built. On-demand briefs/Ask/digest still work.
    # The CVE feeds (NVD, CISA KEV) are the cyber beachhead, and they dominate by
    # volume: 19,276 of 27,194 articles and 77% of all events, none of which ever
    # reached the general feed. Off while the product is India news; re-enable
    # with the Cyber tier. Their corpus was deleted 2026-09-05 and costs nothing
    # to rebuild — public feeds, deterministic enrichment, no LLM.
    # A HARD CEILING ON THE CORPUS, checked before every collector run.
    #
    # "Bounded article cap" and "watched" are not cost controls, and calling them
    # that is how a budget goes. This is a real stop condition: once the corpus
    # holds this many enriched articles, collection stops by itself whether or
    # not anyone is looking. 0 disables the ceiling.
    #
    # It bounds the CORPUS, not the spend directly — spend is LLM calls, retries
    # and briefs, which no article count predicts exactly. But it is the one
    # quantity that cannot drift, and it fails safe: the check runs before
    # collection, so exceeding it costs nothing further.
    prism_ingest_max_articles: int = 0
    prism_cve_feeds_enabled: bool = False
    prism_ingestion_enabled: bool = True

    # Grounded storyline veto master switch. Set PRISM_VETO_ENABLED=false to stop
    # the hourly LLM overlay pass.
    #
    # Turned OFF in production 2026-07-30 because the pass pays for itself roughly
    # never. Two independent losses: persist_veto_overlay does its LLM work, then
    # publishes only if its base run is STILL current (correlation/partition.py:683)
    # — with a 15-minute base cadence and a ~13-minute veto it loses that race about
    # half the time. And when it DOES win, persist_base_run unconditionally
    # republishes with veto_state='pending' on the next tick, so the refinement is
    # discarded within 15 minutes. Measured: of 10 retained runs exactly one carried
    # an applied veto, and it survived 4m33s.
    #
    # Re-enable once the base pass carries a previous run's veto decisions forward
    # instead of dropping them; until then this is an hourly LLM bill for a
    # refinement almost nobody is served.
    prism_veto_enabled: bool = True

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
    #
    # OFF BY DEFAULT, and deliberately so: the self-hosted stack (web + worker +
    # Postgres + Redis + ClickHouse + MinIO) cost $70 in its first two weeks,
    # more than the LLM spend it was there to observe. It is now configured to
    # scale to zero after 10 idle minutes, which means ANY background trace wakes
    # the whole stack and starts billing again. A pipeline that traces by default
    # would keep it permanently awake, so tracing is opt-in per environment.
    #
    # Setting the keys is NOT enough to enable it — that was the old rule, and it
    # made "cost" a side effect of "credentials are present", which is not a
    # decision anyone makes on purpose. Set PRISM_LANGFUSE_ENABLED=true when you
    # actually want to look at traces.
    prism_langfuse_enabled: bool = False
    langfuse_public_key: str = Field("", repr=False)
    langfuse_secret_key: str = Field("", repr=False)
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
    prism_admin_token: str = Field("change-me", repr=False)

    # Auth (magic-link, bearer). Web URL is where the verify link points.
    prism_web_url: str = "http://localhost:3000"
    prism_email_provider: str = "console"  # console (dev) | resend
    resend_api_key: str = Field("", repr=False)
    prism_email_from: str = "Prism <onboarding@resend.dev>"  # set to a verified domain sender
    prism_magic_token_ttl_min: int = 15  # magic-link lifetime
    prism_session_ttl_days: int = 30  # bearer session lifetime
    prism_magic_request_cooldown_s: int = 30  # per-email rate limit on link requests
    prism_free_markets_samples: int = 3  # sample grant on signup (D13 Markets-only)

    # Sources
    nvd_api_key: str = Field("", repr=False)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def langfuse_enabled(self) -> bool:
        """Tracing costs money, so it takes an explicit switch AND credentials."""
        return bool(
            self.prism_langfuse_enabled and self.langfuse_public_key and self.langfuse_secret_key
        )


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
