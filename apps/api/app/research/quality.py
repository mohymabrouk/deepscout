from __future__ import annotations

from urllib.parse import urlsplit

from app.research.models import FetchedPage
from app.schemas.research import SourceQuality


class SourceQualityClassifier:
    """Score observable source-quality signals without claiming factual authority.

    This is intentionally deterministic and explainable. It uses transport, publisher
    domain, content, and title signals available after fetching; it never treats a
    domain suffix as proof that a source is correct.
    """

    _institutional_suffixes = (".gov", ".gov.uk", ".edu", ".edu.au", ".ac.uk")
    _positive_terms = {
        "official",
        "documentation",
        "reference",
        "standard",
        "research",
        "paper",
        "guide",
    }
    _caution_terms = {"forum", "social", "advertisement", "sponsored", "opinion"}

    def classify(self, page: FetchedPage) -> SourceQuality:
        parsed = urlsplit(page.url)
        domain = (parsed.hostname or page.domain).lower().rstrip(".")
        searchable = f"{page.title} {page.url}".lower()
        score = 0.5
        reasons: list[tuple[float, str]] = []

        if parsed.scheme == "https":
            score += 0.08
            reasons.append((0.08, "HTTPS transport was used."))
        else:
            score -= 0.12
            reasons.append((-0.12, "The source does not use HTTPS."))

        if domain.endswith(self._institutional_suffixes):
            score += 0.18
            reasons.append((0.18, "The publisher uses an institutional domain."))
        elif domain.endswith(".org"):
            score += 0.06
            reasons.append((0.06, "The publisher uses an organization domain."))

        if page.status_code == 200:
            score += 0.04
            reasons.append((0.04, "The source returned a successful response."))
        elif page.status_code >= 400:
            score -= 0.12
            reasons.append((-0.12, "The source returned an error response."))

        text_length = len(page.text.strip())
        if text_length >= 1200:
            score += 0.12
            reasons.append((0.12, "The page contains substantial extractable text."))
        elif text_length >= 400:
            score += 0.06
            reasons.append((0.06, "The page contains a useful amount of extractable text."))
        else:
            score -= 0.1
            reasons.append((-0.1, "The page contains limited extractable text."))

        if page.title.strip():
            score += 0.04
            reasons.append((0.04, "The source provides a descriptive title."))
        else:
            score -= 0.04
            reasons.append((-0.04, "The source has no descriptive title."))

        positive_terms = sorted(term for term in self._positive_terms if term in searchable)
        if positive_terms:
            score += min(0.12, 0.04 * len(positive_terms))
            reasons.append((0.04, f"Publisher language includes: {', '.join(positive_terms[:3])}."))
        caution_terms = sorted(term for term in self._caution_terms if term in searchable)
        if caution_terms:
            score -= min(0.18, 0.06 * len(caution_terms))
            reasons.append((-0.06, f"Publisher language includes caution signals: {', '.join(caution_terms[:3])}."))

        score = round(max(0.0, min(1.0, score)), 2)
        label = "high" if score >= 0.75 else "medium" if score >= 0.5 else "low"
        ranked_reasons = sorted(reasons, key=lambda item: abs(item[0]), reverse=True)
        return SourceQuality(score=score, label=label, reasons=[reason for _, reason in ranked_reasons[:5]])
