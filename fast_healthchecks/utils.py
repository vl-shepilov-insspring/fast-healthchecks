"""Utility functions for fast-healthchecks."""

from __future__ import annotations

import ipaddress
from typing import Any
from urllib.parse import unquote, urlparse

REDACT_PLACEHOLDER = "***"
_SECRET_KEYS = frozenset({"http_auth", "password", "sasl_plain_password", "sasl_plain_username", "user", "username"})


def validate_url_ssrf(
    url: str,
    *,
    allowed_schemes: frozenset[str] = frozenset({"http", "https"}),
    block_private_hosts: bool = False,
) -> None:
    """Validate URL for SSRF-sensitive use (e.g. healthchecks from config).

    Args:
        url: The URL string to validate.
        allowed_schemes: Schemes permitted (default http, https).
        block_private_hosts: If True, reject localhost and private IP ranges.

    Raises:
        ValueError: If scheme is not allowed or host is in blocked range.
    """
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in allowed_schemes:
        msg = f"URL scheme must be one of {sorted(allowed_schemes)}, got {scheme!r}"
        raise ValueError(msg)
    if not block_private_hosts:
        return
    host = (parsed.hostname or "").strip()
    if not host:
        return
    if host.lower() in {"localhost", "localhost.", "localhost6", "localhost6.localdomain6"}:
        msg = "URL host must not be localhost when block_private_hosts=True"
        raise ValueError(msg)
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return
    if addr.is_loopback or addr.is_private or addr.is_reserved:
        msg = "URL host must not be loopback or private when block_private_hosts=True"
        raise ValueError(msg)


__all__ = ("maybe_redact", "parse_query_string", "redact_secrets_in_dict", "validate_url_ssrf")


def redact_secrets_in_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of data with credential fields replaced by placeholder."""
    return {k: (REDACT_PLACEHOLDER if k in _SECRET_KEYS else v) for k, v in data.items()}


def maybe_redact(data: dict[str, Any], *, redact_secrets: bool) -> dict[str, Any]:
    """Return data with secrets redacted if requested, otherwise return as-is."""
    return redact_secrets_in_dict(data) if redact_secrets else data


def parse_query_string(query: str) -> dict[str, str]:
    """Parse a URL query string into a dictionary.

    Keys and values are URL-decoded (unquoted). Pairs without '=' are stored
    with an empty value. Values containing '=' are preserved.

    Args:
        query: The query string (e.g. 'key1=value1&key2=value2').

    Returns:
        A dictionary of key-value pairs.
    """
    if not query:
        return {}
    result: dict[str, str] = {}
    for part in query.split("&"):
        kv = part.split("=", 1)
        key = unquote(kv[0]) if kv[0] else ""
        value = unquote(kv[1]) if len(kv) > 1 else ""
        result[key] = value
    return result
