"""Unit tests for checks/dsn_parsing.py."""

from urllib.parse import urlsplit

import pytest

from fast_healthchecks.checks.dsn_parsing import (
    VALID_SSLMODES,
    KafkaParseDSNResult,
    MongoParseDSNResult,
    OpenSearchParseDSNResult,
    ParsedUrl,
    PostgresParseDSNResult,
    RabbitMQParseDSNResult,
)

pytestmark = pytest.mark.unit


def test_valid_sslmodes() -> None:
    assert (
        frozenset(
            {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"},
        )
        == VALID_SSLMODES
    )


def test_parsed_url_type_alias() -> None:
    result = urlsplit("postgresql://localhost/db")
    assert isinstance(result, ParsedUrl)


def test_typed_dict_structures() -> None:
    """Verify TypedDict shapes are usable."""
    kafka: KafkaParseDSNResult = {
        "bootstrap_servers": "localhost:9092",
        "sasl_plain_username": None,
        "sasl_plain_password": None,
        "security_protocol": "PLAINTEXT",
    }
    assert kafka["bootstrap_servers"] == "localhost:9092"

    mongo: MongoParseDSNResult = {
        "parse_result": urlsplit("mongodb://localhost"),
        "authSource": "admin",
    }
    assert mongo["authSource"] == "admin"

    opensearch: OpenSearchParseDSNResult = {"hosts": ["localhost:9200"], "http_auth": None, "use_ssl": False}
    assert opensearch["hosts"] == ["localhost:9200"]

    rabbitmq: RabbitMQParseDSNResult = {"parse_result": urlsplit("amqp://localhost")}
    assert "parse_result" in rabbitmq

    postgres: PostgresParseDSNResult = {
        "parse_result": urlsplit("postgresql://localhost"),
        "sslmode": "disable",
        "sslcert": None,
        "sslkey": None,
        "sslrootcert": None,
        "sslctx": None,
    }
    assert postgres["sslmode"] == "disable"
