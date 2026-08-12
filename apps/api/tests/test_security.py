import pytest
from app.core.errors import DomainError
from app.core.security import anonymous_identity, validate_fetch_url


@pytest.mark.parametrize(
    "url",
    ["http://127.0.0.1", "http://localhost/admin", "http://169.254.169.254/latest", "ftp://example.com"],
)
def test_private_and_unsupported_fetch_urls_are_rejected(url):
    with pytest.raises(DomainError):
        validate_fetch_url(url)


def test_anonymous_identity_does_not_expose_ip():
    identity = anonymous_identity("192.0.2.10", "a" * 32)
    assert identity.startswith("anon_")
    assert "192.0.2.10" not in identity

