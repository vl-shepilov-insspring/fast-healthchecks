"""This module provides a health check class for MongoDB.

Classes:
    MongoHealthCheck: A class to perform health checks on MongoDB.

Usage:
    The MongoHealthCheck class can be used to perform health checks on MongoDB by calling it.

Example:
    health_check = MongoHealthCheck(
        hosts=["host1:27017", "host2:27017"],
        # or hosts="localhost",
        port=27017,
        user="myuser",
        password="mypassword",
        database="mydatabase"
    )
    result = await health_check()
    print(result.healthy)
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Any, final
from urllib.parse import urlsplit

from fast_healthchecks.checks._base import (
    DEFAULT_HC_TIMEOUT,
    ClientCachingMixin,
    HealthCheckDSN,
    healthcheck_safe,
)
from fast_healthchecks.checks._imports import raise_optional_import_error
from fast_healthchecks.checks.dsn_parsing import MongoParseDSNResult
from fast_healthchecks.models import HealthCheckResult
from fast_healthchecks.utils import parse_query_string

try:
    from motor.motor_asyncio import AsyncIOMotorClient
except ImportError as exc:
    raise_optional_import_error("motor", "motor", exc)


@final
class MongoHealthCheck(ClientCachingMixin, HealthCheckDSN[HealthCheckResult]):
    """A class to perform health checks on MongoDB.

    Attributes:
        _auth_source: The MongoDB authentication source.
        _database: The MongoDB database to use.
        _hosts: The MongoDB host or a list of hosts.
        _name: The name of the health check.
        _password: The MongoDB password.
        _port: The MongoDB port.
        _timeout: The timeout for the health check.
        _user: The MongoDB user.
    """

    __slots__ = (
        "_auth_source",
        "_client",
        "_client_loop",
        "_database",
        "_ensure_client_lock",
        "_hosts",
        "_name",
        "_password",
        "_port",
        "_timeout",
        "_user",
    )

    _hosts: str | list[str]
    _port: int | None
    _user: str | None
    _password: str | None
    _database: str | None
    _auth_source: str
    _timeout: float
    _name: str
    _client: AsyncIOMotorClient[dict[str, Any]] | None
    _client_loop: asyncio.AbstractEventLoop | None

    def __init__(  # noqa: PLR0913
        self,
        *,
        hosts: str | list[str] = "localhost",
        port: int | None = 27017,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        auth_source: str = "admin",
        timeout: float = DEFAULT_HC_TIMEOUT,
        name: str = "MongoDB",
    ) -> None:
        """Initialize the MongoHealthCheck.

        Args:
            hosts: The MongoDB host or list of hosts.
            port: The MongoDB port (used when hosts is a single string).
            user: The MongoDB user.
            password: The MongoDB password.
            database: The MongoDB database to use.
            auth_source: The MongoDB authentication source.
            timeout: The timeout for the health check.
            name: The name of the health check.
        """
        self._hosts = hosts
        self._port = port
        self._user = user
        self._password = password
        self._database = database
        self._auth_source = auth_source
        self._timeout = timeout
        self._name = name
        super().__init__()

    def _create_client(self) -> AsyncIOMotorClient[dict[str, Any]]:
        return AsyncIOMotorClient(
            host=self._hosts,
            port=self._port,
            username=self._user,
            password=self._password,
            authSource=self._auth_source,
            serverSelectionTimeoutMS=int(self._timeout * 1000),
        )

    def _close_client(self, client: AsyncIOMotorClient[dict[str, Any]]) -> Awaitable[None]:  # noqa: PLR6301
        result = client.close()
        if asyncio.iscoroutine(result):
            return result

        async def _noop() -> None:
            pass

        return _noop()

    @classmethod
    def _allowed_schemes(cls) -> tuple[str, ...]:
        return ("mongodb", "mongodb+srv")

    @classmethod
    def _default_name(cls) -> str:
        return "MongoDB"

    @classmethod
    def parse_dsn(cls, dsn: str) -> MongoParseDSNResult:
        """Parse the DSN and return the results.

        Args:
            dsn: The DSN to parse.

        Returns:
            MongoParseDSNResult: The results of parsing the DSN.
        """
        parse_result = urlsplit(dsn)
        query = parse_query_string(parse_result.query)
        return {"parse_result": parse_result, "authSource": query.get("authSource", "admin")}

    @classmethod
    def _from_parsed_dsn(
        cls,
        parsed: MongoParseDSNResult,
        *,
        name: str = "MongoDB",
        timeout: float = DEFAULT_HC_TIMEOUT,
        **kwargs: Any,  # noqa: ARG003, ANN401
    ) -> MongoHealthCheck:
        parse_result = parsed["parse_result"]
        hosts: str | list[str]
        port: int | None
        if "," in parse_result.netloc:
            hosts = parse_result.netloc.split("@")[-1].split(",")
            port = None
        else:
            hosts = parse_result.hostname or "localhost"
            port = parse_result.port or 27017
        return cls(
            hosts=hosts,
            port=port,
            user=parse_result.username,
            password=parse_result.password,
            database=parse_result.path.lstrip("/") or None,
            auth_source=parsed["authSource"],
            timeout=timeout,
            name=name,
        )

    @healthcheck_safe(invalidate_on_error=True)
    async def __call__(self) -> HealthCheckResult:
        """Perform the health check on MongoDB.

        Returns:
            HealthCheckResult: The result of the health check.
        """
        client = await self._ensure_client()
        database = client[self._database] if self._database else client[self._auth_source]
        res = await database.command("ping")
        ok_raw = res.get("ok")
        ok_value = ok_raw if isinstance(ok_raw, (bool, int, float)) else 0
        return HealthCheckResult(name=self._name, healthy=int(ok_value) == 1)

    def _build_dict(self) -> dict[str, Any]:
        return {
            "hosts": self._hosts,
            "port": self._port,
            "user": self._user,
            "password": self._password,
            "database": self._database,
            "auth_source": self._auth_source,
            "timeout": self._timeout,
            "name": self._name,
        }
