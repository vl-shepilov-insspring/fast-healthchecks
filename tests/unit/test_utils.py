import pytest

from fast_healthchecks.utils import (
    maybe_redact,
    parse_query_string,
    redact_secrets_in_dict,
    validate_url_ssrf,
)

pytestmark = pytest.mark.unit


def test_redact_secrets_in_dict() -> None:
    data = {
        "host": "x",
        "password": "secret",
        "user": "u",
        "username": "admin",
        "sasl_plain_password": "pwd",
    }
    result = redact_secrets_in_dict(data)
    assert result["host"] == "x"
    assert result["user"] == "***"
    assert result["username"] == "***"
    assert result["password"] == "***"
    assert result["sasl_plain_password"] == "***"


def test_maybe_redact_with_redaction() -> None:
    data = {"user": "u", "password": "p"}
    result = maybe_redact(data, redact_secrets=True)
    assert result["user"] == "***"
    assert result["password"] == "***"


def test_maybe_redact_without_redaction() -> None:
    data = {"user": "u", "password": "p"}
    result = maybe_redact(data, redact_secrets=False)
    assert result == data


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("", {}),
        ("sslmode=disable", {"sslmode": "disable"}),
        ("sslcert=%2Ftmp%2Fclient.crt", {"sslcert": "/tmp/client.crt"}),
        ("key%20name=value", {"key name": "value"}),
        ("key=value=value2", {"key": "value=value2"}),
        ("a=1&b=2", {"a": "1", "b": "2"}),
        ("a=1&b", {"a": "1", "b": ""}),
    ],
)
def test_parse_query_string(query: str, expected: dict[str, str]) -> None:
    assert parse_query_string(query) == expected


def test_validate_url_ssrf_allows_http_https() -> None:
    validate_url_ssrf("https://example.com/")
    validate_url_ssrf("http://example.com/path")
    validate_url_ssrf("HTTPS://example.com/")


def test_validate_url_ssrf_rejects_bad_scheme() -> None:
    with pytest.raises(ValueError, match=r"URL scheme must be one of"):
        validate_url_ssrf("file:///etc/passwd")
    with pytest.raises(ValueError, match=r"URL scheme must be one of"):
        validate_url_ssrf("gopher://localhost/")


def test_validate_url_ssrf_block_private_rejects_localhost() -> None:
    with pytest.raises(ValueError, match=r"must not be localhost"):
        validate_url_ssrf("http://localhost/", block_private_hosts=True)
    with pytest.raises(ValueError, match=r"must not be localhost"):
        validate_url_ssrf("http://localhost:8080/", block_private_hosts=True)


def test_validate_url_ssrf_block_private_rejects_loopback_ip() -> None:
    with pytest.raises(ValueError, match=r"must not be loopback"):
        validate_url_ssrf("http://127.0.0.1/", block_private_hosts=True)
    with pytest.raises(ValueError, match=r"must not be loopback"):
        validate_url_ssrf("http://[::1]/", block_private_hosts=True)


def test_validate_url_ssrf_block_private_rejects_private_ip() -> None:
    with pytest.raises(ValueError, match=r"must not be loopback"):
        validate_url_ssrf("http://192.168.1.1/", block_private_hosts=True)
    with pytest.raises(ValueError, match=r"must not be loopback"):
        validate_url_ssrf("http://10.0.0.1/", block_private_hosts=True)


def test_validate_url_ssrf_block_private_allows_public() -> None:
    validate_url_ssrf("https://example.com/", block_private_hosts=True)


def test_validate_url_ssrf_block_private_empty_host_skips_check() -> None:
    validate_url_ssrf("https:///", block_private_hosts=True)
