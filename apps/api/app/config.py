from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Limits live here so deployments can tighten them safely."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_version: str = "0.1.0"
    frontend_origin: str = "http://localhost:3000"
    api_public_url: str = "http://localhost:8000"
    database_url: str | None = None
    anon_id_hmac_secret: str = Field(default="local-development-secret", min_length=16)
    supabase_url: str | None = None
    supabase_jwt_secret: str | None = None
    supabase_jwt_jwks_url: str | None = None
    supabase_jwt_audience: str = "authenticated"
    enable_auth: bool = False
    enable_history: bool = True

    llm_provider: str = "demo"
    llm_api_key: str | None = None
    llm_model: str = "demo"
    llm_timeout_seconds: float = 25.0
    provider_max_retries: int = Field(default=1, ge=0, le=3)
    provider_retry_backoff_seconds: float = Field(default=0.2, ge=0, le=5)
    llm_fallback_enabled: bool = False
    llm_fallback_provider: str | None = None
    llm_fallback_api_key: str | None = None
    llm_fallback_model: str | None = None

    search_provider: str = "demo"
    search_api_key: str | None = None
    search_timeout_seconds: float = 10.0

    anon_runs_per_day: int = Field(default=5, ge=0)
    auth_runs_per_day: int = Field(default=15, ge=0)
    anon_concurrent_runs: int = Field(default=1, ge=1)
    auth_concurrent_runs: int = Field(default=2, ge=1)
    http_requests_per_minute_anon: int = Field(default=30, ge=1)
    http_requests_per_minute_auth: int = Field(default=60, ge=1)

    max_question_chars: int = Field(default=1500, ge=10)
    max_search_queries: int = Field(default=3, ge=1)
    max_search_results_per_query: int = Field(default=5, ge=1)
    max_fetched_pages: int = Field(default=6, ge=1)
    max_fetch_bytes: int = Field(default=3_000_000, ge=1024)
    fetch_timeout_seconds: float = Field(default=8.0, gt=0)
    fetch_concurrency: int = Field(default=3, ge=1)
    max_extracted_chars_per_source: int = Field(default=12_000, ge=100)
    max_total_context_chars: int = Field(default=50_000, ge=100)
    max_llm_calls_per_run: int = Field(default=3, ge=1)
    max_input_tokens_per_run: int = Field(default=18_000, ge=1)
    max_output_tokens_per_run: int = Field(default=2_500, ge=1)
    max_run_seconds: float = Field(default=60.0, gt=0)
    max_request_bytes: int = Field(default=64_000, ge=1024)

    log_level: str = "INFO"
    store_question_text: bool = False
    enable_fallback_provider: bool = True
    enable_debug_usage: bool = False

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.app_env.lower() in {"production", "prod"}:
            if self.anon_id_hmac_secret == "local-development-secret":
                raise ValueError("ANON_ID_HMAC_SECRET must be replaced in production.")
            if not self.database_url:
                raise ValueError("DATABASE_URL is required in production.")
            if self.llm_provider == "demo" or not self.llm_api_key:
                raise ValueError("A production LLM provider and API key are required.")
            if self.search_provider == "demo" or not self.search_api_key:
                raise ValueError("A production search provider and API key are required.")
        if self.enable_auth and not self.supabase_jwt_secret and not self.supabase_jwt_jwks_url:
            if not self.supabase_url:
                raise ValueError("SUPABASE_URL or a Supabase JWT verification key is required.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
