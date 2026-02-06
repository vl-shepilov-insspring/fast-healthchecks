"""This module provides a health check class for OpenSearch.

Classes:
    OpenSearchHealthCheck: A class to perform health checks on OpenSearch.

Usage:
    The OpenSearchHealthCheck class can be used to perform health checks on OpenSearch by calling it.

Example:
    health_check = OpenSearchHealthCheck(
        hosts=["localhost:9200"],
        http_auth=("username", "password"),
        use_ssl=True,
        verify_certs=True,
        ssl_show_warn=False,
        ca_certs="/path/to/ca.pem",
    )
    result = await health_check()
    print(result.healthy)
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Any, cast, final
from urllib.parse import unquote, urlsplit

from fast_healthchecks.checks._base import (
    DEFAULT_HC_TIMEOUT,
    ClientCachingMixin,
    HealthCheckDSN,
    healthcheck_safe,
)
from fast_healthchecks.checks._imports import raise_optional_import_error
from fast_healthchecks.checks.dsn_parsing import OpenSearchParseDSNResult
from fast_healthchecks.models import HealthCheckResult

try:
    from opensearchpy import AsyncOpenSearch
except ImportError as exc:
    raise_optional_import_error("opensearch", "opensearch-py", exc)


@final
class OpenSearchHealthCheck(ClientCachingMixin, HealthCheckDSN[HealthCheckResult]):
    """A class to perform health checks on OpenSearch.

    Attributes:
        _hosts: The OpenSearch hosts.
        _name: The name of the health check.
        _http_auth: The HTTP authentication.
        _use_ssl: Whether to use SSL or not.
        _verify_certs: Whether to verify certificates or not.
        _ssl_show_warn: Whether to show SSL warnings or not.
        _ca_certs: The CA certificates.
        _timeout: The timeout for the health check.
    """

    __slots__ = (
        "_ca_certs",
        "_client",
        "_client_loop",
        "_ensure_client_lock",
        "_hosts",
        "_http_auth",
        "_name",
        "_ssl_show_warn",
        "_timeout",
        "_use_ssl",
        "_verify_certs",
    )

    _hosts: list[str]
    _http_auth: tuple[str, str] | None
    _use_ssl: bool
    _verify_certs: bool
    _ssl_show_warn: bool
    _ca_certs: str | None
    _timeout: float
    _name: str
    _client: AsyncOpenSearch | None
    _client_loop: asyncio.AbstractEventLoop | None

    def __init__(  # noqa: PLR0913
        self,
        *,
        hosts: list[str],
        http_auth: tuple[str, str] | None = None,
        use_ssl: bool = False,
        verify_certs: bool = False,
        ssl_show_warn: bool = False,
        ca_certs: str | None = None,
        timeout: float = DEFAULT_HC_TIMEOUT,
        name: str = "OpenSearch",
    ) -> None:
        """Initialize the OpenSearchHealthCheck.

        Args:
            hosts: The OpenSearch hosts.
            http_auth: The HTTP authentication.
            use_ssl: Whether to use SSL or not.
            verify_certs: Whether to verify certificates or not.
            ssl_show_warn: Whether to show SSL warnings or not.
            ca_certs: The CA certificates.
            timeout: The timeout for the health check.
            name: The name of the health check.
        """
        self._hosts = hosts
        self._http_auth = http_auth
        self._use_ssl = use_ssl
        self._verify_certs = verify_certs
        self._ssl_show_warn = ssl_show_warn
        self._ca_certs = ca_certs
        self._timeout = timeout
        self._name = name
        super().__init__()

    def _create_client(self) -> AsyncOpenSearch:
        return AsyncOpenSearch(
            hosts=self._hosts,
            http_auth=self._http_auth,
            use_ssl=self._use_ssl,
            verify_certs=self._verify_certs,
            ssl_show_warn=self._ssl_show_warn,
            ca_certs=self._ca_certs,
            timeout=self._timeout,
        )

    def _close_client(self, client: AsyncOpenSearch) -> Awaitable[None]:  # noqa: PLR6301
        return client.close()

    @classmethod
    def _allowed_schemes(cls) -> tuple[str, ...]:
        return ("http", "https")

    @classmethod
    def _default_name(cls) -> str:
        return "OpenSearch"

    @classmethod
    def parse_dsn(cls, dsn: str) -> OpenSearchParseDSNResult:
        """Parse the OpenSearch DSN and return the results.

        Args:
            dsn: The DSN to parse.

        Returns:
            OpenSearchParseDSNResult: The results of parsing the DSN.

        Raises:
            ValueError: If DSN has missing host.
        """
        parsed = urlsplit(dsn)
        if not parsed.hostname:
            msg = "OpenSearch DSN must include a host"
            raise ValueError(msg) from None

        http_auth: tuple[str, str] | None = None
        if parsed.username is not None:
            http_auth = (unquote(parsed.username), unquote(parsed.password or ""))

        port = parsed.port or (443 if parsed.scheme == "https" else 9200)
        return {
            "hosts": [f"{parsed.hostname}:{port}"],
            "http_auth": http_auth,
            "use_ssl": parsed.scheme == "https",
        }

    @classmethod
    def _from_parsed_dsn(
        cls,
        parsed: OpenSearchParseDSNResult,
        *,
        name: str = "OpenSearch",
        timeout: float = DEFAULT_HC_TIMEOUT,
        **kwargs: Any,  # noqa: ANN401
    ) -> OpenSearchHealthCheck:
        return cls(
            hosts=parsed["hosts"],
            http_auth=parsed["http_auth"],
            use_ssl=parsed["use_ssl"],
            verify_certs=cast("bool", kwargs.get("verify_certs", False)),
            ssl_show_warn=cast("bool", kwargs.get("ssl_show_warn", False)),
            ca_certs=cast("str | None", kwargs.get("ca_certs")),
            timeout=timeout,
            name=name,
        )

    @healthcheck_safe(invalidate_on_error=True)
    async def __call__(self) -> HealthCheckResult:
        """Perform the health check on OpenSearch.

        Returns:
            HealthCheckResult: The result of the health check.
        """
        client = await self._ensure_client()
        await client.info()
        return HealthCheckResult(name=self._name, healthy=True)

    def _build_dict(self) -> dict[str, Any]:
        return {
            "hosts": self._hosts,
            "http_auth": self._http_auth,
            "use_ssl": self._use_ssl,
            "verify_certs": self._verify_certs,
            "ssl_show_warn": self._ssl_show_warn,
            "ca_certs": self._ca_certs,
            "timeout": self._timeout,
            "name": self._name,
        }
