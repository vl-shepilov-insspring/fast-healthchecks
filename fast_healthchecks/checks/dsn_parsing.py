"""Shared DSN parsing types for health checks."""

from __future__ import annotations

import ssl
from typing import TYPE_CHECKING, Literal, TypeAlias, TypedDict
from urllib.parse import ParseResult, SplitResult

ParsedUrl: TypeAlias = ParseResult | SplitResult

if TYPE_CHECKING:
    from redis.asyncio.connection import ConnectKwargs

__all__ = (
    "VALID_SSLMODES",
    "KafkaParseDSNResult",
    "MongoParseDSNResult",
    "OpenSearchParseDSNResult",
    "ParsedUrl",
    "PostgresParseDSNResult",
    "RabbitMQParseDSNResult",
    "RedisParseDSNResult",
    "SslMode",
)


class RedisParseDSNResult(TypedDict, total=True):
    """Result of parsing a Redis DSN."""

    parse_result: ConnectKwargs
    scheme: str


SslMode: TypeAlias = Literal["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
VALID_SSLMODES: frozenset[str] = frozenset({"disable", "allow", "prefer", "require", "verify-ca", "verify-full"})


class KafkaParseDSNResult(TypedDict, total=True):
    """Result of parsing a Kafka DSN."""

    bootstrap_servers: str
    sasl_plain_username: str | None
    sasl_plain_password: str | None
    security_protocol: str


class MongoParseDSNResult(TypedDict, total=True):
    """Result of parsing a MongoDB DSN."""

    parse_result: ParsedUrl
    authSource: str


class OpenSearchParseDSNResult(TypedDict, total=True):
    """Result of parsing an OpenSearch DSN."""

    hosts: list[str]
    http_auth: tuple[str, str] | None
    use_ssl: bool


class RabbitMQParseDSNResult(TypedDict, total=True):
    """Result of parsing a RabbitMQ/AMQP DSN."""

    parse_result: ParsedUrl


class PostgresParseDSNResult(TypedDict, total=True):
    """Result of parsing a PostgreSQL DSN."""

    parse_result: ParsedUrl
    sslmode: SslMode
    sslcert: str | None
    sslkey: str | None
    sslrootcert: str | None
    sslctx: ssl.SSLContext | None
