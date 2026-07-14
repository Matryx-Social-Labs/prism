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

    # Per-stage models (swap based on Langfuse eval scores)
    prism_model_gate: str = "deepseek-v4-flash:cloud"
    prism_model_classify: str = "gemma4:31b-cloud"
    prism_model_extract: str = "qwen3.5:397b-cloud"
    prism_model_correlate: str = "qwen3.5:397b-cloud"
    prism_model_agent: str = "gpt-oss:120b-cloud"
    prism_model_judge: str = "glm-5.2:cloud"

    # Embeddings (fastembed, in-process). Changing the model to one with a
    # different dimension requires a migration of the vector(...) columns.
    prism_embed_model: str = "BAAI/bge-small-en-v1.5"
    prism_embed_dim: int = 384

    # Langfuse (self-hosted). The SDK also reads LANGFUSE_* env vars directly;
    # these mirror them so app code can check whether tracing is configured.
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = ""

    # API
    cors_origins: str = "http://localhost:3000"
    prism_admin_token: str = "change-me"

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
    return Settings()
