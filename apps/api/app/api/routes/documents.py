from __future__ import annotations

import hashlib
from pathlib import PurePath

from fastapi import APIRouter, File, Request, UploadFile

from app.core.errors import DomainError
from app.documents import DocumentExtractionError, extract_pdf
from app.schemas.research import DocumentAccepted

router = APIRouter(prefix="/v1/documents", tags=["documents"])


@router.post("", response_model=DocumentAccepted, status_code=201)
async def upload_document(request: Request, file: UploadFile = File(...)) -> DocumentAccepted:
    settings = request.app.state.settings
    filename = PurePath(file.filename or "document.pdf").name[:255]
    if not filename.lower().endswith(".pdf"):
        raise DomainError("INVALID_DOCUMENT", "Only PDF files may be uploaded.", 400)
    payload = await file.read(settings.max_document_bytes + 1)
    await file.close()
    if len(payload) > settings.max_document_bytes:
        raise DomainError("DOCUMENT_TOO_LARGE", "The PDF exceeds the configured byte limit.", 413)
    if not payload.startswith(b"%PDF-"):
        raise DomainError("INVALID_DOCUMENT", "The uploaded file is not a PDF.", 400)
    try:
        text, page_count = extract_pdf(
            payload, settings.max_document_pages, settings.max_document_chars
        )
    except DocumentExtractionError as exc:
        raise DomainError("INVALID_DOCUMENT", str(exc), 400) from exc
    document = await request.app.state.repository.create_document(
        filename=filename,
        extracted_text=text,
        page_count=page_count,
        content_hash=hashlib.sha256(payload).hexdigest(),
        identity_key=request.state.identity_key,
        user_id=request.state.user_id,
    )
    return DocumentAccepted(
        id=document.id,
        filename=document.filename,
        page_count=document.page_count,
        character_count=len(document.extracted_text),
    )
