from __future__ import annotations

import hashlib
import hmac
import ipaddress
from urllib.parse import urlsplit

from .errors import DomainError


def anonymous_identity(raw_ip: str, secret: str) -> str:
    """Return a stable, non-reversible identity without persisting the raw address."""
    try:
        address = ipaddress.ip_address(raw_ip)
        normalized = str(ipaddress.ip_network(f"{address}/24", strict=False).network_address)
    except ValueError:
        normalized = "invalid"
    return "anon_" + hmac.new(secret.encode(), normalized.encode(), hashlib.sha256).hexdigest()


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
        raise DomainError("INVALID_REQUEST", "Only absolute http(s) URLs may be fetched.", 400)
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in {"localhost", "metadata.google.internal"}:
        raise DomainError("INVALID_REQUEST", "Private network URLs are not fetchable.", 400)
    try:
        if not is_public_ip(hostname):
            # Hostnames are resolved by the fetcher and checked before connection.
            if "." not in hostname:
                raise DomainError("INVALID_REQUEST", "Private network URLs are not fetchable.", 400)
    except ValueError:
        raise DomainError("INVALID_REQUEST", "Invalid fetch URL.", 400) from None
    return parsed._replace(fragment="").geturl()

