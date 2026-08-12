from __future__ import annotations

from io import BytesIO

from app.documents import DocumentExtractionError, extract_pdf
from app.main import create_app
from fastapi.testclient import TestClient


def make_pdf(text: str) -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(text) + 34} >>\nstream\nBT /F1 12 Tf 72 720 Td ({text}) Tj ET\nendstream".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    payload = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(payload))
        payload.extend(f"{index} 0 obj\n".encode())
        payload.extend(obj)
        payload.extend(b"\nendobj\n")
    xref = len(payload)
    payload.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        payload.extend(f"{offset:010d} 00000 n \n".encode())
    payload.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(payload)


def test_pdf_extraction_is_bounded_and_rejects_empty_text():
    text, pages = extract_pdf(make_pdf("A sufficiently long sentence that should be extracted from the uploaded PDF."), 5, 500)
    assert pages == 1
    assert "sufficiently long" in text
    try:
        extract_pdf(b"%PDF-1.4 invalid", 5, 500)
    except DocumentExtractionError:
        pass
    else:
        raise AssertionError("invalid PDFs must be rejected")


def test_pdf_upload_and_owned_run_attachment():
    app = create_app()
    with TestClient(app) as client:
        response = client.post(
            "/v1/documents",
            files={"file": ("notes.pdf", BytesIO(make_pdf("The uploaded document contains a bounded research note.")), "application/pdf")},
        )
        assert response.status_code == 201
        document = response.json()
        accepted = client.post(
            "/v1/research",
            json={
                "question": "What does the uploaded research note contain?",
                "document_ids": [document["id"]],
            },
        )
        assert accepted.status_code == 202


def test_non_pdf_upload_is_rejected():
    app = create_app()
    with TestClient(app) as client:
        response = client.post(
            "/v1/documents",
            files={"file": ("notes.txt", BytesIO(b"not a pdf"), "text/plain")},
        )
        assert response.status_code == 400
