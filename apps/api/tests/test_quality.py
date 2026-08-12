from datetime import UTC, datetime

from app.research.models import FetchedPage
from app.research.quality import SourceQualityClassifier


def page(url: str, title: str, text: str, status_code: int = 200) -> FetchedPage:
    return FetchedPage(
        url=url,
        title=title,
        text=text,
        domain=url.split("/")[2],
        retrieved_at=datetime.now(UTC),
        status_code=status_code,
    )


def test_quality_classifier_is_explainable_and_bounded():
    quality = SourceQualityClassifier().classify(
        page(
            "https://research.example.edu/official-reference",
            "Official research reference guide",
            "evidence " * 300,
        )
    )
    assert quality.label == "high"
    assert 0 <= quality.score <= 1
    assert quality.reasons
    assert any("institutional" in reason.lower() for reason in quality.reasons)


def test_quality_classifier_marks_short_http_caution_source_low():
    quality = SourceQualityClassifier().classify(
        page("http://forum.example.com/opinion", "Forum opinion", "Too short", 200)
    )
    assert quality.label == "low"
    assert quality.score < 0.5
    assert any("https" in reason.lower() for reason in quality.reasons)
    assert any("caution" in reason.lower() for reason in quality.reasons)
