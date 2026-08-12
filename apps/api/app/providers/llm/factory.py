from app.config import Settings
from app.core.errors import PROVIDER_UNAVAILABLE, DomainError
from app.research.models import LLMProvider

from .demo import DemoLLMProvider
from .openai_compatible import OpenAICompatibleProvider


def create_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "demo":
        return DemoLLMProvider()
    if not settings.llm_api_key:
        raise DomainError(
            PROVIDER_UNAVAILABLE, "The configured inference provider has no API key.", 503
        )
    bases = {
        "groq": "https://api.groq.com/openai/v1",
        "openrouter": "https://openrouter.ai/api/v1",
    }
    base_url = bases.get(settings.llm_provider)
    if not base_url:
        raise DomainError(
            PROVIDER_UNAVAILABLE, "The configured inference provider is unsupported.", 503
        )
    return OpenAICompatibleProvider(
        settings.llm_provider,
        settings.llm_api_key,
        settings.llm_model,
        base_url,
        settings.llm_timeout_seconds,
    )
