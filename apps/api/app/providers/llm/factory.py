from app.config import Settings
from app.core.errors import PROVIDER_UNAVAILABLE, DomainError
from app.research.models import LLMProvider

from .demo import DemoLLMProvider
from .openai_compatible import OpenAICompatibleProvider
from .reliable import ReliableLLMProvider


def _compatible_provider(
    provider: str, api_key: str | None, model: str, timeout: float
) -> LLMProvider:
    if not api_key:
        raise DomainError(
            PROVIDER_UNAVAILABLE, "The configured inference provider has no API key.", 503
        )
    bases = {"groq": "https://api.groq.com/openai/v1", "openrouter": "https://openrouter.ai/api/v1"}
    base_url = bases.get(provider)
    if not base_url:
        raise DomainError(
            PROVIDER_UNAVAILABLE, "The configured inference provider is unsupported.", 503
        )
    return OpenAICompatibleProvider(provider, api_key, model, base_url, timeout)


def create_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "demo":
        return ReliableLLMProvider(
            DemoLLMProvider(),
            None,
            settings.provider_max_retries,
            settings.provider_retry_backoff_seconds,
        )
    primary = _compatible_provider(
        settings.llm_provider,
        settings.llm_api_key,
        settings.llm_model,
        settings.llm_timeout_seconds,
    )
    fallback = None
    if settings.enable_fallback_provider and settings.llm_fallback_enabled and settings.llm_fallback_provider:
        fallback = _compatible_provider(
            settings.llm_fallback_provider,
            settings.llm_fallback_api_key,
            settings.llm_fallback_model or settings.llm_model,
            settings.llm_timeout_seconds,
        )
    return ReliableLLMProvider(
        primary,
        fallback,
        settings.provider_max_retries,
        settings.provider_retry_backoff_seconds,
    )
