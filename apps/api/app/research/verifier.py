from __future__ import annotations

from app.research.models import EvidencePassage
from app.schemas.research import ResearchReport


class CitationVerifier:
    def verify(
        self, report: ResearchReport, evidence: list[EvidencePassage]
    ) -> tuple[ResearchReport, list[str]]:
        valid_ids = set(range(1, len(evidence) + 1))
        invalid = False
        for section in report.sections:
            for paragraph in section.paragraphs:
                original = list(paragraph.citations)
                paragraph.citations = list(
                    dict.fromkeys(citation for citation in original if citation in valid_ids)
                )
                invalid = invalid or original != paragraph.citations
        limitations = list(report.limitations)
        if invalid:
            limitations.append(
                "Some citation references were removed because they did not match fetched sources."
            )
        if any(
            not paragraph.citations
            for section in report.sections
            for paragraph in section.paragraphs
        ):
            limitations.append("Citation coverage may be incomplete for some paragraphs.")
        report.limitations = list(dict.fromkeys(limitations))
        return report, limitations
