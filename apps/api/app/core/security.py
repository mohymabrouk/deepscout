from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit
from uuid import UUID

import jwt

from app.config import Settings

from .errors import AUTH_NOT_CONFIGURED, INVALID_REQUEST, UNAUTHORIZED, DomainError


@dataclass(frozen=True)
class AuthUser:
    """Identity extracted from a verified Supabase access token."""

    user_id: str
    email: str | None = None


def anonymous_identity(raw_ip: str, secret: str) -> str:
    """Return a stable, non-reversible identity without persisting the raw address."""
    try:
        address = ipaddress.ip_address(raw_ip)
        normalized = str(ipaddress.ip_network(f"{address}/24", strict=False).network_address)
    except ValueError:
        normalized = "invalid"
    return "anon_" + hmac.new(secret.encode(), normalized.encode(), hashlib.sha256).hexdigest()


def authenticated_identity(user_id: str, secret: str) -> str:
    """Return an opaque quota key for a verified user ID."""
    return "user_" + hmac.new(secret.encode(), user_id.encode(), hashlib.sha256).hexdigest()


def authenticate_request(authorization: str | None, settings: Settings) -> AuthUser | None:
    """Validate a Supabase JWT and return only claims safe for authorization decisions."""
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise DomainError(UNAUTHORIZED, "Authentication is required or the token is invalid.", 401)
    if not settings.enable_auth:
        raise DomainError(AUTH_NOT_CONFIGURED, "Authentication is not enabled for this API.", 503)
    jwks_url = settings.supabase_jwt_jwks_url
    if not settings.supabase_jwt_secret and not jwks_url:
        if settings.supabase_url:
            jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        else:
            raise DomainError(AUTH_NOT_CONFIGURED, "Authentication is not configured for this API.", 503)

    issuer = None
    if settings.supabase_url:
        issuer = f"{settings.supabase_url.rstrip('/')}/auth/v1"
    try:
        decode_kwargs = {"audience": settings.supabase_jwt_audience}
        if issuer:
            decode_kwargs["issuer"] = issuer
        if settings.supabase_jwt_secret:
            claims = jwt.decode(
                token.strip(), settings.supabase_jwt_secret, algorithms=["HS256"], **decode_kwargs
            )
        else:
            signing_key = jwt.PyJWKClient(jwks_url).get_signing_key_from_jwt(token.strip())
            claims = jwt.decode(
                token.strip(),
                signing_key.key,
                algorithms=["RS256", "ES256", "EdDSA"],
                **decode_kwargs,
            )
        user_id = str(UUID(str(claims.get("sub", ""))))
    except (jwt.InvalidTokenError, ValueError, TypeError, OSError):
        raise DomainError(UNAUTHORIZED, "Authentication is required or the token is invalid.", 401) from None

    if claims.get("role") != "authenticated":
        raise DomainError(UNAUTHORIZED, "Authentication is required or the token is invalid.", 401)
    email = claims.get("email")
    return AuthUser(user_id=user_id, email=email if isinstance(email, str) else None)


def encode_cursor(created_at: datetime, run_id: str, secret: str) -> str:
    payload = json.dumps(
        {"created_at": created_at.astimezone(UTC).isoformat(), "id": run_id},
        separators=(",", ":"),
    ).encode()
    encoded = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    signature = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def decode_cursor(cursor: str, secret: str) -> tuple[datetime, str]:
    try:
        encoded, signature = cursor.rsplit(".", 1)
        expected = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        padded = encoded + "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
        created_at = datetime.fromisoformat(payload["created_at"]).astimezone(UTC)
        run_id = str(payload["id"])
        if not run_id:
            raise ValueError
        return created_at, run_id
    except (ValueError, KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        raise DomainError(INVALID_REQUEST, "The history cursor is invalid.", 400) from None


def is_public_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def validate_fetch_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise DomainError(INVALID_REQUEST, "Only absolute http(s) URLs may be fetched.", 400)
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in {"localhost", "metadata.google.internal"}:
        raise DomainError(INVALID_REQUEST, "Private network URLs are not fetchable.", 400)
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        if "." not in hostname:
            raise DomainError(INVALID_REQUEST, "Private network URLs are not fetchable.", 400)
    else:
        if not is_public_ip(str(address)):
            raise DomainError(INVALID_REQUEST, "Private network URLs are not fetchable.", 400)
    return parsed._replace(fragment="").geturl()
