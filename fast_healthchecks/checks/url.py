"""This module provides a health check class for URLs.

Classes:
    UrlHealthCheck: A class to perform health checks on URLs.

Usage:
    The UrlHealthCheck class can be used to perform health checks on URLs by calling it.

Example:
    health_check = UrlHealthCheck(
        url="https://www.google.com",
    )
    result = await health_check()
    print(result.healthy)
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, final

from fast_healthchecks.checks._base import (
    DEFAULT_HC_TIMEOUT,
    ClientCachingMixin,
    HealthCheck,
    ToDictMixin,
    healthcheck_safe,
)
from fast_healthchecks.checks._imports import raise_optional_import_error
from fast_healthchecks.models import HealthCheckResult
from fast_healthchecks.utils import validate_url_ssrf

try:
    from httpx import AsyncClient, AsyncHTTPTransport, BasicAuth, Response
except ImportError as exc:
    raise_optional_import_error("httpx", "httpx", exc)

if TYPE_CHECKING:
    from httpx._types import URLTypes


@final
class UrlHealthCheck(ClientCachingMixin, ToDictMixin, HealthCheck[HealthCheckResult]):
    """A class to perform health checks on URLs.

    Attributes:
        _name: The name of the health check.
        _password: The password to authenticate with.
        _timeout: The timeout for the connection.
        _url: The URL to connect to.
        _username: The user to authenticate with.
        _verify_ssl: Whether to verify the SSL certificate.
    """

    __slots__ = (
        "_auth",
        "_block_private_hosts",
        "_client",
        "_client_loop",
        "_ensure_client_lock",
        "_follow_redirects",
        "_name",
        "_password",
        "_timeout",
        "_transport",
        "_url",
        "_username",
        "_verify_ssl",
    )

    _url: URLTypes
    _username: str | None
    _password: str | None
    _auth: BasicAuth | None
    _verify_ssl: bool
    _transport: AsyncHTTPTransport | None
    _follow_redirects: bool
    _timeout: float
    _name: str
    _client: AsyncClient | None
    _client_loop: asyncio.AbstractEventLoop | None

    def __init__(  # noqa: PLR0913
        self,
        *,
        url: URLTypes,
        username: str | None = None,
        password: str | None = None,
        verify_ssl: bool = True,
        follow_redirects: bool = True,
        timeout: float = DEFAULT_HC_TIMEOUT,
        name: str = "HTTP",
        block_private_hosts: bool = False,
    ) -> None:
        """Initialize the health check.

        Warning:
            Pass only trusted URLs from application configuration. Do not use
            user-controlled input for ``url`` to avoid SSRF.

        Args:
            url: The URL to connect to.
            username: The user to authenticate with.
            password: The password to authenticate with.
            verify_ssl: Whether to verify the SSL certificate.
            follow_redirects: Whether to follow redirects.
            timeout: The timeout for the connection.
            name: The name of the health check.
            block_private_hosts: If True, reject localhost and private IP hosts.
        """
        validate_url_ssrf(str(url), block_private_hosts=block_private_hosts)
        self._url = url
        self._block_private_hosts = block_private_hosts
        self._username = username
        self._password = password
        self._auth = BasicAuth(self._username, self._password or "") if self._username else None
        self._verify_ssl = verify_ssl
        self._transport = AsyncHTTPTransport(verify=self._verify_ssl)
        self._follow_redirects = follow_redirects
        self._timeout = timeout
        self._name = name
        super().__init__()

    def _create_client(self) -> AsyncClient:
        return AsyncClient(
            auth=self._auth,
            timeout=self._timeout,
            transport=self._transport,
            follow_redirects=self._follow_redirects,
        )

    def _close_client(self, client: AsyncClient) -> Awaitable[None]:  # noqa: PLR6301
        return client.aclose()

    @healthcheck_safe(invalidate_on_error=True)
    async def __call__(self) -> HealthCheckResult:
        """Perform the health check.

        Returns:
            HealthCheckResult: The result of the health check.
        """
        client = await self._ensure_client()
        response: Response = await client.get(self._url)
        if response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR or (
            self._username and response.status_code in {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN}
        ):
            response.raise_for_status()
        return HealthCheckResult(name=self._name, healthy=response.is_success)

    def _build_dict(self) -> dict[str, Any]:
        return {
            "url": str(self._url),
            "username": self._username,
            "password": self._password,
            "verify_ssl": self._verify_ssl,
            "follow_redirects": self._follow_redirects,
            "timeout": self._timeout,
            "name": self._name,
            "block_private_hosts": self._block_private_hosts,
        }
