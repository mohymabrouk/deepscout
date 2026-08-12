from app.config import Settings
from app.core.errors import SEARCH_UNAVAILABLE, DomainError
from app.research.models import SearchProvider

from .demo import DemoSearchProvider
from .http import BraveSearchProvider
from .reliable import ReliableSearchProvider


def create_search_provider(settings: Settings) -> SearchProvider:
    if settings.search_provider in {"", "demo"}:
        return ReliableSearchProvider(
            DemoSearchProvider(),
            settings.provider_max_retries,
            settings.provider_retry_backoff_seconds,
        )
    if settings.search_provider == "brave" and settings.search_api_key:
        return ReliableSearchProvider(
            BraveSearchProvider(settings.search_api_key, settings.search_timeout_seconds),
            settings.provider_max_retries,
            settings.provider_retry_backoff_seconds,
        )
    raise DomainError(SEARCH_UNAVAILABLE, "The configured search provider is unavailable.", 503)
