"""This module provides a health check class for RabbitMQ.

Classes:
    RabbitMQHealthCheck: A class to perform health checks on RabbitMQ.

Usage:
    The RabbitMQHealthCheck class can be used to perform health checks on RabbitMQ by calling it.

Example:
    health_check = RabbitMQHealthCheck(
        host="localhost",
        port=5672,
        username="guest",
        password="guest",
    )
    result = await health_check()
    print(result.healthy)
"""

from __future__ import annotations

from typing import Any, final
from urllib.parse import urlsplit

from fast_healthchecks.checks._base import DEFAULT_HC_TIMEOUT, HealthCheckDSN, healthcheck_safe
from fast_healthchecks.checks._imports import raise_optional_import_error
from fast_healthchecks.checks.dsn_parsing import RabbitMQParseDSNResult
from fast_healthchecks.models import HealthCheckResult

try:
    import aio_pika
except ImportError as exc:
    raise_optional_import_error("aio-pika", "aio-pika", exc)


@final
class RabbitMQHealthCheck(HealthCheckDSN[HealthCheckResult]):
    """A class to perform health checks on RabbitMQ.

    Attributes:
        _host: The RabbitMQ host.
        _name: The name of the health check.
        _password: The RabbitMQ password.
        _port: The RabbitMQ port.
        _secure: Whether to use a secure connection.
        _timeout: The timeout for the health check.
        _user: The RabbitMQ user.
        _vhost: The RabbitMQ virtual host.
    """

    __slots__ = ("_host", "_name", "_password", "_port", "_secure", "_timeout", "_user", "_vhost")

    _host: str
    _port: int
    _secure: bool
    _user: str
    _vhost: str
    _password: str
    _timeout: float
    _name: str

    def __init__(  # noqa: PLR0913
        self,
        *,
        host: str,
        user: str,
        password: str,
        port: int = 5672,
        vhost: str = "/",
        secure: bool = False,
        timeout: float = DEFAULT_HC_TIMEOUT,
        name: str = "RabbitMQ",
    ) -> None:
        """Initialize the RabbitMQHealthCheck.

        Args:
            host: The RabbitMQ host.
            user: The RabbitMQ user
            password: The RabbitMQ password
            port: The RabbitMQ port
            vhost: The RabbitMQ virtual host
            secure: Whether to use a secure connection
            timeout: The timeout for the health check
            name: The name of the health check
        """
        self._host = host
        self._user = user
        self._password = password
        self._port = port
        self._vhost = vhost
        self._secure = secure
        self._timeout = timeout
        self._name = name

    @classmethod
    def _allowed_schemes(cls) -> tuple[str, ...]:
        return ("amqp", "amqps")

    @classmethod
    def _default_name(cls) -> str:
        return "RabbitMQ"

    @classmethod
    def parse_dsn(cls, dsn: str) -> RabbitMQParseDSNResult:
        """Parse the DSN and return the results.

        Args:
            dsn: The DSN to parse.

        Returns:
            RabbitMQParseDSNResult: The results of parsing the DSN.
        """
        parse_result = urlsplit(dsn)
        return {"parse_result": parse_result}

    @classmethod
    def _from_parsed_dsn(
        cls,
        parsed: RabbitMQParseDSNResult,
        *,
        name: str = "RabbitMQ",
        timeout: float = DEFAULT_HC_TIMEOUT,
        **kwargs: Any,  # noqa: ARG003, ANN401
    ) -> RabbitMQHealthCheck:
        parse_result = parsed["parse_result"]
        return cls(
            host=parse_result.hostname or "localhost",
            user=parse_result.username or "guest",
            password=parse_result.password or "guest",
            port=parse_result.port or 5672,
            vhost=parse_result.path.lstrip("/") or "/",
            secure=parse_result.scheme == "amqps",
            timeout=timeout,
            name=name,
        )

    @healthcheck_safe(invalidate_on_error=False)
    async def __call__(self) -> HealthCheckResult:
        """Perform the health check on RabbitMQ.

        Returns:
            HealthCheckResult: The result of the health check.
        """
        async with await aio_pika.connect_robust(
            host=self._host,
            port=self._port,
            login=self._user,
            password=self._password,
            ssl=self._secure,
            virtualhost=self._vhost,
            timeout=self._timeout,
        ):
            return HealthCheckResult(name=self._name, healthy=True)

    def _build_dict(self) -> dict[str, Any]:
        return {
            "host": self._host,
            "user": self._user,
            "password": self._password,
            "port": self._port,
            "vhost": self._vhost,
            "secure": self._secure,
            "timeout": self._timeout,
            "name": self._name,
        }
