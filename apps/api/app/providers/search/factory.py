from app.config import Settings
from app.core.errors import SEARCH_UNAVAILABLE, DomainError
from app.research.models import SearchProvider

from .demo import DemoSearchProvider
from .http import BraveSearchProvider


def create_search_provider(settings: Settings) -> SearchProvider:
    if settings.search_provider in {"", "demo"}:
        return DemoSearchProvider()
    if settings.search_provider == "brave" and settings.search_api_key:
        return BraveSearchProvider(settings.search_api_key, settings.search_timeout_seconds)
    raise DomainError(SEARCH_UNAVAILABLE, "The configured search provider is unavailable.", 503)
