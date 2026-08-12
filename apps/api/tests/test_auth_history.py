from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from app.config import Settings
from app.core.security import decode_cursor, encode_cursor
from app.main import create_app
from fastapi.testclient import TestClient

SECRET = "test-supabase-jwt-secret-32-bytes"


def token(user_id: str) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "aud": "authenticated",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        SECRET,
        algorithm="HS256",
    )


@pytest.fixture
def auth_app(monkeypatch):
    import app.main as main_module

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(enable_auth=True, supabase_jwt_secret=SECRET),
    )
    return create_app()


def test_invalid_bearer_token_is_rejected(auth_app):
    with TestClient(auth_app) as client:
        response = client.get("/v1/runs", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_history_is_owned_and_delete_is_owner_only(auth_app):
    owner = str(uuid4())
    other_user = str(uuid4())
    owner_headers = {"Authorization": f"Bearer {token(owner)}"}
    other_headers = {"Authorization": f"Bearer {token(other_user)}"}

    with TestClient(auth_app) as client:
        accepted = client.post(
            "/v1/research",
            json={"question": "Explain how ownership checks protect run history."},
            headers=owner_headers,
        )
        assert accepted.status_code == 202
        run_id = accepted.json()["run_id"]

        history = client.get("/v1/runs", headers=owner_headers)
        assert history.status_code == 200
        assert history.json()["items"][0]["id"] == run_id

        assert client.get(f"/v1/research/{run_id}", headers=owner_headers).status_code == 200
        assert client.get(f"/v1/research/{run_id}", headers=other_headers).status_code == 404
        assert client.delete(f"/v1/runs/{run_id}", headers=other_headers).status_code == 404
        assert client.delete(f"/v1/runs/{run_id}", headers=owner_headers).status_code == 204
        assert client.get(f"/v1/research/{run_id}", headers=owner_headers).status_code == 404


def test_history_cursor_is_signed():
    created_at = datetime.now(UTC)
    cursor = encode_cursor(created_at, "run-id", SECRET)
    assert decode_cursor(cursor, SECRET)[1] == "run-id"
    with pytest.raises(Exception):
        decode_cursor(cursor + "tampered", SECRET)
