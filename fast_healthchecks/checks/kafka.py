"""This module provides a health check class for Kafka.

Classes:
    KafkaHealthCheck: A class to perform health checks on Kafka.

Usage:
    The KafkaHealthCheck class can be used to perform health checks on Kafka by calling it.

Example:
    health_check = KafkaHealthCheck(
        bootstrap_servers="localhost:9092",
        security_protocol="PLAINTEXT",
    )
    result = await health_check()
    print(result.healthy)
"""

from __future__ import annotations

import asyncio
import ssl
from collections.abc import Awaitable
from typing import Any, Literal, TypeAlias, cast, final
from urllib.parse import unquote, urlsplit

from fast_healthchecks.checks._base import (
    DEFAULT_HC_TIMEOUT,
    ClientCachingMixin,
    HealthCheckDSN,
    healthcheck_safe,
)
from fast_healthchecks.checks._imports import raise_optional_import_error
from fast_healthchecks.checks.dsn_parsing import KafkaParseDSNResult
from fast_healthchecks.models import HealthCheckResult

try:
    from aiokafka.admin import AIOKafkaAdminClient
except ImportError as exc:
    raise_optional_import_error("aiokafka", "aiokafka", exc)

SecurityProtocol: TypeAlias = Literal["SSL", "PLAINTEXT", "SASL_PLAINTEXT", "SASL_SSL"]
SaslMechanism: TypeAlias = Literal["PLAIN", "GSSAPI", "SCRAM-SHA-256", "SCRAM-SHA-512", "OAUTHBEARER"]

VALID_SECURITY_PROTOCOLS: frozenset[str] = frozenset({"SSL", "PLAINTEXT", "SASL_PLAINTEXT", "SASL_SSL"})
VALID_SASL_MECHANISMS: frozenset[str] = frozenset({"PLAIN", "GSSAPI", "SCRAM-SHA-256", "SCRAM-SHA-512", "OAUTHBEARER"})


@final
class KafkaHealthCheck(ClientCachingMixin, HealthCheckDSN[HealthCheckResult]):
    """A class to perform health checks on Kafka.

    Attributes:
        _bootstrap_servers: The Kafka bootstrap servers.
        _name: The name of the health check.
        _sasl_mechanism: The SASL mechanism to use.
        _sasl_plain_password: The SASL plain password.
        _sasl_plain_username: The SASL plain username.
        _security_protocol: The security protocol to use.
        _ssl_context: The SSL context to use.
        _timeout: The timeout for the health check.
    """

    __slots__ = (
        "_bootstrap_servers",
        "_client",
        "_client_loop",
        "_ensure_client_lock",
        "_name",
        "_sasl_mechanism",
        "_sasl_plain_password",
        "_sasl_plain_username",
        "_security_protocol",
        "_ssl_context",
        "_timeout",
    )

    _bootstrap_servers: str
    _ssl_context: ssl.SSLContext | None
    _security_protocol: SecurityProtocol
    _sasl_mechanism: SaslMechanism
    _sasl_plain_username: str | None
    _sasl_plain_password: str | None
    _timeout: float
    _name: str
    _client: AIOKafkaAdminClient | None
    _client_loop: asyncio.AbstractEventLoop | None

    def __init__(  # noqa: PLR0913
        self,
        *,
        bootstrap_servers: str,
        ssl_context: ssl.SSLContext | None = None,
        security_protocol: SecurityProtocol = "PLAINTEXT",
        sasl_mechanism: SaslMechanism = "PLAIN",
        sasl_plain_username: str | None = None,
        sasl_plain_password: str | None = None,
        timeout: float = DEFAULT_HC_TIMEOUT,
        name: str = "Kafka",
    ) -> None:
        """Initialize the KafkaHealthCheck.

        Args:
            bootstrap_servers: The Kafka bootstrap servers.
            ssl_context: The SSL context to use.
            security_protocol: The security protocol to use.
            sasl_mechanism: The SASL mechanism to use.
            sasl_plain_username: The SASL plain username.
            sasl_plain_password: The SASL plain password.
            timeout: The timeout for the health check.
            name: The name of the health check.

        Raises:
            ValueError: If the security protocol or SASL mechanism is invalid.
        """
        self._bootstrap_servers = bootstrap_servers
        self._ssl_context = ssl_context
        if security_protocol not in VALID_SECURITY_PROTOCOLS:
            msg = f"Invalid security protocol: {security_protocol}"
            raise ValueError(msg) from None
        self._security_protocol = security_protocol
        if sasl_mechanism not in VALID_SASL_MECHANISMS:
            msg = f"Invalid SASL mechanism: {sasl_mechanism}"
            raise ValueError(msg) from None
        self._sasl_mechanism = sasl_mechanism
        self._sasl_plain_username = sasl_plain_username
        self._sasl_plain_password = sasl_plain_password
        self._timeout = timeout
        self._name = name
        super().__init__()

    def _create_client(self) -> AIOKafkaAdminClient:
        return AIOKafkaAdminClient(
            bootstrap_servers=self._bootstrap_servers,
            client_id="fast_healthchecks",
            request_timeout_ms=int(self._timeout * 1000),
            ssl_context=self._ssl_context,
            security_protocol=self._security_protocol,
            sasl_mechanism=self._sasl_mechanism,
            sasl_plain_username=self._sasl_plain_username,
            sasl_plain_password=self._sasl_plain_password,
        )

    def _close_client(self, client: AIOKafkaAdminClient) -> Awaitable[None]:  # noqa: PLR6301
        return client.close()

    @classmethod
    def _allowed_schemes(cls) -> tuple[str, ...]:
        return ("kafka", "kafkas")

    @classmethod
    def _default_name(cls) -> str:
        return "Kafka"

    @classmethod
    def parse_dsn(cls, dsn: str) -> KafkaParseDSNResult:
        """Parse the Kafka DSN and return the results.

        Scheme ``kafkas`` implies SSL (SASL_SSL when credentials present).
        Scheme ``kafka`` implies PLAINTEXT (SASL_PLAINTEXT when credentials present).
        Kwargs to from_dsn override DSN-derived values.

        Args:
            dsn: The DSN to parse.

        Returns:
            KafkaParseDSNResult: The results of parsing the DSN.

        Raises:
            ValueError: If bootstrap servers are missing.
        """
        parsed = urlsplit(dsn)
        scheme = (parsed.scheme or "kafka").lower()
        netloc = parsed.netloc
        sasl_plain_username: str | None = None
        sasl_plain_password: str | None = None
        if "@" in netloc:
            userinfo, hosts = netloc.rsplit("@", 1)
            netloc = hosts
            if ":" in userinfo:
                username, password = userinfo.split(":", 1)
                sasl_plain_username = unquote(username) or None
                sasl_plain_password = unquote(password) or None
            else:
                sasl_plain_username = unquote(userinfo) or None

        bootstrap_servers = netloc or parsed.path.lstrip("/")
        if not bootstrap_servers:
            msg = "Kafka DSN must include bootstrap servers"
            raise ValueError(msg) from None

        if scheme == "kafkas":
            security_protocol = "SASL_SSL" if (sasl_plain_username or sasl_plain_password) else "SSL"
        else:
            security_protocol = "SASL_PLAINTEXT" if (sasl_plain_username or sasl_plain_password) else "PLAINTEXT"

        return {
            "bootstrap_servers": bootstrap_servers,
            "sasl_plain_username": sasl_plain_username,
            "sasl_plain_password": sasl_plain_password,
            "security_protocol": security_protocol,
        }

    @classmethod
    def _from_parsed_dsn(
        cls,
        parsed: KafkaParseDSNResult,
        *,
        name: str = "Kafka",
        timeout: float = DEFAULT_HC_TIMEOUT,
        **kwargs: Any,  # noqa: ANN401
    ) -> KafkaHealthCheck:
        return cls(
            bootstrap_servers=parsed["bootstrap_servers"],
            ssl_context=cast("ssl.SSLContext | None", kwargs.get("ssl_context")),
            security_protocol=cast(
                "SecurityProtocol",
                kwargs.get("security_protocol", parsed["security_protocol"]),
            ),
            sasl_mechanism=cast("SaslMechanism", kwargs.get("sasl_mechanism", "PLAIN")),
            sasl_plain_username=parsed["sasl_plain_username"],
            sasl_plain_password=parsed["sasl_plain_password"],
            timeout=timeout,
            name=name,
        )

    @healthcheck_safe(invalidate_on_error=True)
    async def __call__(self) -> HealthCheckResult:
        """Perform the health check on Kafka.

        Returns:
            HealthCheckResult: The result of the health check.
        """
        client = await self._ensure_client()
        await client.start()
        await client.list_topics()
        return HealthCheckResult(name=self._name, healthy=True)

    def _build_dict(self) -> dict[str, Any]:
        return {
            "bootstrap_servers": self._bootstrap_servers,
            "ssl_context": self._ssl_context,
            "security_protocol": self._security_protocol,
            "sasl_mechanism": self._sasl_mechanism,
            "sasl_plain_username": self._sasl_plain_username,
            "sasl_plain_password": self._sasl_plain_password,
            "timeout": self._timeout,
            "name": self._name,
        }
