from __future__ import annotations

import re

from app.research.models import EvidencePassage, FetchedPage


def _terms(value: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9][a-z0-9-]{2,}", value.lower())}


class EvidenceSelector:
    def __init__(self, max_context_chars: int = 50_000, max_sources: int = 6) -> None:
        self.max_context_chars = max_context_chars
        self.max_sources = max_sources

    def select(
        self, question: str, pages: list[FetchedPage], must_cover: list[str] | None = None
    ) -> list[EvidencePassage]:
        query_terms = _terms(question + " " + " ".join(must_cover or []))
        candidates: list[EvidencePassage] = []
        for index, page in enumerate(pages, start=1):
            paragraphs = [
                part.strip()
                for part in re.split(r"\n+|(?<=[.!?])\s+", page.text)
                if len(part.strip()) >= 25
            ]
            if not paragraphs:
                paragraphs = [page.text]
            scored = []
            for paragraph in paragraphs:
                terms = _terms(paragraph)
                overlap = len(query_terms & terms)
                score = overlap / max(1, len(query_terms))
                scored.append((score, paragraph))
            score, excerpt = max(scored, key=lambda item: item[0])
            candidates.append(EvidencePassage(index, page, excerpt[:1800], score))
        candidates.sort(key=lambda item: item.relevance_score, reverse=True)
        selected: list[EvidencePassage] = []
        selected_indexes: set[int] = set()
        domains: set[str] = set()
        total = 0
        for item in candidates:
            if len(selected) >= self.max_sources or total >= self.max_context_chars:
                continue
            if item.source.domain in domains and len(domains) < min(3, self.max_sources):
                continue
            remaining = self.max_context_chars - total
            slots_left = max(1, self.max_sources - len(selected))
            excerpt_limit = max(1, remaining // slots_left)
            selected.append(
                EvidencePassage(
                    item.source_index,
                    item.source,
                    item.excerpt[:excerpt_limit],
                    item.relevance_score,
                )
            )
            selected_indexes.add(item.source_index)
            domains.add(item.source.domain)
            total += min(len(item.excerpt), excerpt_limit)
        for item in candidates:
            if (
                len(selected) >= self.max_sources
                or item.source_index in selected_indexes
                or total >= self.max_context_chars
            ):
                continue
            remaining = self.max_context_chars - total
            selected.append(
                EvidencePassage(
                    item.source_index,
                    item.source,
                    item.excerpt[:remaining],
                    item.relevance_score,
                )
            )
            total += min(len(item.excerpt), remaining)
        return selected
