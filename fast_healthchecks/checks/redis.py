"""This module provides a health check class for Redis.

Classes:
    RedisHealthCheck: A class to perform health checks on Redis.

Usage:
    The RedisHealthCheck class can be used to perform health checks on Redis by calling it.

Example:
    health_check = RedisHealthCheck(
        host="localhost",
        port=6379,
    )
    result = await health_check()
    print(result.healthy)
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any, final
from urllib.parse import urlsplit

from fast_healthchecks.checks._base import (
    DEFAULT_HC_TIMEOUT,
    ClientCachingMixin,
    HealthCheckDSN,
    healthcheck_safe,
)
from fast_healthchecks.checks._imports import raise_optional_import_error
from fast_healthchecks.checks.dsn_parsing import RedisParseDSNResult
from fast_healthchecks.models import HealthCheckResult

try:
    from redis.asyncio import Redis
    from redis.asyncio.connection import parse_url
except ImportError as exc:
    raise_optional_import_error("redis", "redis", exc)

if TYPE_CHECKING:
    from redis.asyncio.connection import ConnectKwargs


@final
class RedisHealthCheck(ClientCachingMixin, HealthCheckDSN[HealthCheckResult]):
    """A class to perform health checks on Redis.

    Attributes:
        _database: The database to connect to.
        _host: The host to connect to.
        _name: The name of the health check.
        _password: The password to authenticate with.
        _port: The port to connect to.
        _timeout: The timeout for the connection.
        _user: The user to authenticate with.
        _ssl: Whether to use SSL or not.
        _ssl_ca_certs: The path to the CA certificate.
    """

    __slots__ = (
        "_client",
        "_client_loop",
        "_database",
        "_ensure_client_lock",
        "_host",
        "_name",
        "_password",
        "_port",
        "_ssl",
        "_ssl_ca_certs",
        "_timeout",
        "_user",
    )

    _host: str
    _port: int
    _database: str | int
    _user: str | None
    _password: str | None
    _timeout: float
    _name: str
    _ssl: bool
    _ssl_ca_certs: str | None
    _client: Redis | None
    _client_loop: asyncio.AbstractEventLoop | None

    def __init__(  # noqa: PLR0913
        self,
        *,
        host: str = "localhost",
        port: int = 6379,
        database: str | int = 0,
        user: str | None = None,
        password: str | None = None,
        ssl: bool = False,
        ssl_ca_certs: str | None = None,
        timeout: float | None = DEFAULT_HC_TIMEOUT,
        name: str = "Redis",
    ) -> None:
        """Initialize the RedisHealthCheck class.

        Args:
            host: The host to connect to.
            port: The port to connect to.
            database: The database to connect to.
            user: The user to authenticate with.
            password: The password to authenticate with.
            ssl: Whether to use SSL.
            ssl_ca_certs: Path to CA certificates for SSL.
            timeout: The timeout for the connection.
            name: The name of the health check.
        """
        self._host = host
        self._port = port
        self._database = database
        self._user = user
        self._password = password
        self._ssl = ssl
        self._ssl_ca_certs = ssl_ca_certs
        self._timeout = DEFAULT_HC_TIMEOUT if timeout is None else timeout
        self._name = name
        super().__init__()

    def _create_client(self) -> Redis:
        return Redis(
            host=self._host,
            port=self._port,
            db=self._database,
            username=self._user,
            password=self._password,
            socket_timeout=self._timeout,
            single_connection_client=True,
            ssl=self._ssl,
            ssl_ca_certs=self._ssl_ca_certs,
        )

    def _close_client(self, client: Redis) -> Awaitable[None]:  # noqa: PLR6301
        return client.aclose()

    @classmethod
    def _allowed_schemes(cls) -> tuple[str, ...]:
        return ("redis", "rediss")

    @classmethod
    def _default_name(cls) -> str:
        return "Redis"

    @classmethod
    def parse_dsn(cls, dsn: str) -> RedisParseDSNResult:
        """Parse the DSN and return the results.

        Args:
            dsn: The DSN to parse.

        Returns:
            RedisParseDSNResult: The results of parsing the DSN.
        """
        parse_result: ConnectKwargs = parse_url(str(dsn))
        scheme = urlsplit(dsn).scheme.lower()
        return {"parse_result": parse_result, "scheme": scheme}

    @classmethod
    def _from_parsed_dsn(
        cls,
        parsed: RedisParseDSNResult,
        *,
        name: str = "Redis",
        timeout: float = DEFAULT_HC_TIMEOUT,
        **kwargs: Any,  # noqa: ARG003, ANN401
    ) -> RedisHealthCheck:
        parse_result = parsed["parse_result"]
        scheme = parsed.get("scheme", "")
        ssl_ca_certs: str | None = parse_result.get("ssl_ca_certs")
        ssl = parse_result.get("ssl", False) or bool(ssl_ca_certs) or (scheme == "rediss")
        return cls(
            host=parse_result.get("host", "localhost"),
            port=parse_result.get("port", 6379),
            database=parse_result.get("db", 0),
            user=parse_result.get("username"),
            password=parse_result.get("password"),
            ssl=ssl,
            ssl_ca_certs=ssl_ca_certs,
            timeout=timeout,
            name=name,
        )

    @healthcheck_safe(invalidate_on_error=True)
    async def __call__(self) -> HealthCheckResult:
        """Perform a health check on Redis.

        Returns:
            HealthCheckResult: The result of the health check.
        """
        redis = await self._ensure_client()
        healthy = bool(await redis.ping())
        return HealthCheckResult(name=self._name, healthy=healthy)

    def _build_dict(self) -> dict[str, Any]:
        return {
            "host": self._host,
            "port": self._port,
            "database": self._database,
            "user": self._user,
            "password": self._password,
            "ssl": self._ssl,
            "ssl_ca_certs": self._ssl_ca_certs,
            "timeout": self._timeout,
            "name": self._name,
        }
