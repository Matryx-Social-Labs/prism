import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Infrastructure
    database_url: str = "postgresql+asyncpg://prism:prism@localhost:5432/prism"
    redis_url: str = "redis://localhost:6379/0"

    # Ollama Cloud (OpenAI-compatible)
    ollama_api_key: str = ""
    ollama_base_url: str = "https://ollama.com/v1"

    # Per-stage models (swap based on Langfuse eval scores).
    # Measured on Ollama Cloud (July 2026): glm-5.2 extracts in ~5s with
    # quality equal to qwen3.5:397b at ~107s — fast models guard the
    # high-volume stages; the big model judges evals (low volume).
    prism_model_gate: str = "deepseek-v4-flash:cloud"
    prism_model_classify: str = "gemma4:31b-cloud"
    prism_model_extract: str = "glm-5.2:cloud"
    # Cheap extraction for low-stakes sectors (sports/entertainment/health/
    # science) — the all-sector expansion would blow the GPU quota on glm-5.2.
    prism_model_extract_light: str = "deepseek-v4-flash:cloud"
    prism_model_correlate: str = "glm-5.2:cloud"
    prism_model_agent: str = "gpt-oss:120b-cloud"
    prism_model_judge: str = "qwen3.5:397b-cloud"

    # Embeddings (fastembed, in-process). Changing the model to one with a
    # different dimension requires a migration of the vector(...) columns.
    prism_embed_model: str = "BAAI/bge-small-en-v1.5"
    prism_embed_dim: int = 384

    # Relevance gate — embedding pre-filter (freemium-lens-model PR0).
    # shadow: score every LLM-gated item with embeddings and LOG (score,
    # llm_decision) for calibration, without changing what gets filtered.
    # Flip to "enforce" only after back-sampling the logs picks a band.
    prism_gate_mode: str = "shadow"  # shadow | enforce | off

    # Langfuse (self-hosted). The SDK also reads LANGFUSE_* env vars directly;
    # these mirror them so app code can check whether tracing is configured.
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = ""

    # API
    cors_origins: str = "http://localhost:3000"
    prism_admin_token: str = "change-me"

    # Auth (magic-link, bearer). Web URL is where the verify link points.
    prism_web_url: str = "http://localhost:3000"
    prism_email_provider: str = "console"  # console (dev) | resend | ses | postmark
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
