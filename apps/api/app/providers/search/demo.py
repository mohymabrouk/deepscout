from __future__ import annotations

from app.research.models import SearchResult


class DemoSearchProvider:
    """Deterministic search fixture with diverse source domains."""

    async def search(self, query: str, limit: int) -> list[SearchResult]:
        sources = [
            (
                "https://demo.local/primary",
                "Primary technical reference",
                "A primary reference covering the core concepts and implementation details.",
            ),
            (
                "https://demo.local/analysis",
                "Independent analysis",
                "An independent analysis covering tradeoffs, cost, and operational limitations.",
            ),
            (
                "https://demo.local/guide",
                "Practical implementation guide",
                "A practical guide describing deployment choices and common failure modes.",
            ),
            (
                "https://demo.local/limitations",
                "Limitations and open questions",
                "A source discussing limitations, uncertainty, and areas requiring further validation.",
            ),
        ]
        return [
            SearchResult(
                url=url, title=title, snippet=f"{snippet} Query: {query}", domain="demo.local"
            )
            for url, title, snippet in sources[:limit]
        ]
