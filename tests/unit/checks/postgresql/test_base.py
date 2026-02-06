"""Unit tests for postgresql/base.py."""

import ssl

import pytest

from fast_healthchecks.checks.postgresql.base import (
    BasePostgreSQLHealthCheck,
    create_ssl_context,
)
from tests.utils import SSL_FILES_MAP, SSLCERT_NAME, SSLKEY_NAME, SSLROOTCERT_NAME

pytestmark = pytest.mark.unit

CA_CRT = str(SSL_FILES_MAP[SSLROOTCERT_NAME])
CERT_CRT = str(SSL_FILES_MAP[SSLCERT_NAME])
KEY_FILE = str(SSL_FILES_MAP[SSLKEY_NAME])

VALID_SSLMODES = {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}


def test_validate_sslmode_valid_modes() -> None:
    for mode in VALID_SSLMODES:
        result = BasePostgreSQLHealthCheck.validate_sslmode(mode)
        assert result == mode


def test_validate_sslmode_invalid_raises() -> None:
    with pytest.raises(ValueError, match=r"Invalid sslmode: invalid"):
        BasePostgreSQLHealthCheck.validate_sslmode("invalid")


def test_parse_minimal_dsn() -> None:
    result = BasePostgreSQLHealthCheck.parse_dsn("postgresql://localhost/db")
    assert result["parse_result"].hostname == "localhost"
    assert result["parse_result"].path == "/db"
    assert result["sslmode"] == "disable"
    assert result["sslcert"] is None
    assert result["sslkey"] is None
    assert result["sslrootcert"] is None


def test_parse_dsn_with_sslmode() -> None:
    result = BasePostgreSQLHealthCheck.parse_dsn(
        "postgresql://localhost/db?sslmode=require",
    )
    assert result["sslmode"] == "require"


def test_parse_dsn_with_ssl_params() -> None:
    result = BasePostgreSQLHealthCheck.parse_dsn(
        f"postgresql://localhost/db?sslmode=verify-full&sslcert={CERT_CRT}&sslkey={KEY_FILE}&sslrootcert={CA_CRT}",
    )
    assert result["sslmode"] == "verify-full"
    assert result["sslcert"] == CERT_CRT
    assert result["sslkey"] == KEY_FILE
    assert result["sslrootcert"] == CA_CRT
    assert result["sslctx"] is not None


def test_parse_dsn_invalid_sslmode_raises() -> None:
    with pytest.raises(ValueError, match=r"Invalid sslmode"):
        BasePostgreSQLHealthCheck.parse_dsn(
            "postgresql://localhost/db?sslmode=bad",
        )


def test_create_ssl_context_disable_returns_none() -> None:
    assert create_ssl_context("disable", None, None, None) is None


def test_create_ssl_context_allow_returns_none() -> None:
    assert create_ssl_context("allow", None, None, None) is None


def test_create_ssl_context_prefer_returns_context() -> None:
    ctx = create_ssl_context("prefer", None, None, None)
    assert isinstance(ctx, ssl.SSLContext)


def test_create_ssl_context_require_returns_context() -> None:
    ctx = create_ssl_context("require", None, None, None)
    assert isinstance(ctx, ssl.SSLContext)
    assert ctx.check_hostname is False
    assert ctx.verify_mode == ssl.CERT_NONE


def test_create_ssl_context_verify_full_requires_sslcert() -> None:
    with pytest.raises(ValueError, match=r"sslcert is required for verify-full"):
        create_ssl_context("verify-full", None, None, "/path/ca")


def test_create_ssl_context_verify_ca_with_cafile() -> None:
    ctx = create_ssl_context("verify-ca", None, None, CA_CRT)
    assert isinstance(ctx, ssl.SSLContext)
    assert ctx.check_hostname is False
    assert ctx.verify_mode == ssl.CERT_REQUIRED


def test_create_ssl_context_cache_returns_same_context() -> None:
    ctx1 = create_ssl_context("require", None, None, None)
    ctx2 = create_ssl_context("require", None, None, None)
    assert ctx1 is ctx2
