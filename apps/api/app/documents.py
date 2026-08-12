from __future__ import annotations

import io
import re

from pypdf import PdfReader


class DocumentExtractionError(ValueError):
    """Raised when a PDF cannot be safely converted to bounded text."""


def extract_pdf(payload: bytes, max_pages: int, max_chars: int) -> tuple[str, int]:
    try:
        reader = PdfReader(io.BytesIO(payload), strict=False)
        page_count = len(reader.pages)
    except Exception as exc:
        raise DocumentExtractionError("The uploaded file is not a readable PDF.") from exc
    if page_count == 0:
        raise DocumentExtractionError("The PDF has no pages.")
    if page_count > max_pages:
        raise DocumentExtractionError("The PDF exceeds the configured page limit.")

    pages: list[str] = []
    total = 0
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            raise DocumentExtractionError("The PDF contains an unreadable page.") from exc
        normalized = re.sub(r"\s+", " ", text.replace("\x00", " ")).strip()
        if not normalized:
            continue
        remaining = max_chars - total
        if remaining <= 0:
            break
        excerpt = normalized[:remaining]
        pages.append(excerpt)
        total += len(excerpt)
    combined = "\n\n".join(pages).strip()
    if len(combined) < 20:
        raise DocumentExtractionError("The PDF did not contain enough extractable text.")
    return combined[:max_chars], page_count
