"""This module contains the base classes for all health checks."""

from __future__ import annotations

import asyncio
import contextlib
import functools
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from traceback import format_exc
from typing import Any, Generic, ParamSpec, Protocol, TypeVar
from urllib.parse import urlsplit

from fast_healthchecks.models import HealthCheckResult
from fast_healthchecks.utils import maybe_redact

T_co = TypeVar("T_co", bound=HealthCheckResult, covariant=True)
P = ParamSpec("P")

__all__ = (
    "DEFAULT_HC_TIMEOUT",
    "ClientCachingMixin",
    "HealthCheck",
    "HealthCheckDSN",
    "ToDictMixin",
    "healthcheck_safe",
    "result_on_error",
)


DEFAULT_HC_TIMEOUT: float = 5.0


def result_on_error(name: str) -> HealthCheckResult:
    """Create a failed HealthCheckResult with current traceback.

    Returns:
        HealthCheckResult: Failed result with error_details from format_exc().
    """
    return HealthCheckResult(name=name, healthy=False, error_details=format_exc())


class _HasName(Protocol):
    _name: str


def healthcheck_safe(
    invalidate_on_error: bool = False,  # noqa: FBT001, FBT002
) -> Callable[
    [Callable[P, Awaitable[HealthCheckResult]]],
    Callable[P, Awaitable[HealthCheckResult]],
]:
    """Decorator that catches exceptions and returns a failed HealthCheckResult.

    Returns:
        A decorator that wraps an async method and returns the decorated method.
    """

    def decorator(
        method: Callable[P, Awaitable[HealthCheckResult]],
    ) -> Callable[P, Awaitable[HealthCheckResult]]:
        @functools.wraps(method)
        async def wrapper(
            self: _HasName,
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> HealthCheckResult:
            try:
                return await method(self, *args, **kwargs)  # type: ignore[arg-type]
            except Exception:  # noqa: BLE001
                if invalidate_on_error:
                    invalidate = getattr(self, "_invalidate_client", None)
                    if callable(invalidate):
                        await invalidate()
                return result_on_error(self._name)

        return wrapper  # type: ignore[return-value]

    return decorator


class ToDictMixin(ABC):
    """Mixin for health checks that support serialization to dict."""

    @abstractmethod
    def _build_dict(self) -> dict[str, Any]:
        """Return the check attributes as a dictionary (without redaction)."""
        ...  # pragma: no cover

    def to_dict(self, *, redact_secrets: bool = False) -> dict[str, Any]:
        """Convert the check to a dictionary.

        Returns:
            dict: Check attributes, optionally with secrets redacted.
        """
        return maybe_redact(self._build_dict(), redact_secrets=redact_secrets)


class ClientCachingMixin(ABC):
    """Mixin for health checks that cache a client and need lifecycle management.

    Use this mixin for checks that maintain a long-lived client (Redis, Kafka,
    Mongo, Url, OpenSearch). Implement _create_client and _close_client.
    Register probes with healthcheck_shutdown() so cached clients are closed
    on app shutdown.

    _close_client(client) must return Awaitable[None]. Checks that create a new connection per call
    (RabbitMQ, PostgreSQL via asyncpg/psycopg) do not use this mixin.
    """

    _client: Any
    _client_loop: asyncio.AbstractEventLoop | None
    _ensure_client_lock: asyncio.Lock

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        super().__init__(*args, **kwargs)
        self._client = None
        self._client_loop = None
        self._ensure_client_lock = asyncio.Lock()

    @abstractmethod
    def _create_client(self) -> Any:  # noqa: ANN401
        """Create and return a new client. Called when cache is empty or invalid."""
        ...  # pragma: no cover

    @abstractmethod
    def _close_client(self, client: Any) -> Awaitable[None]:  # noqa: ANN401
        """Close the client. Must return an awaitable (coroutine)."""
        ...  # pragma: no cover

    async def aclose(self) -> None:
        """Close the cached client if present."""
        async with self._ensure_client_lock:
            if self._client is not None:
                await self._close_client(self._client)
                self._client = None
                self._client_loop = None

    async def _ensure_client(self) -> Any:  # noqa: ANN401
        """Return cached client, creating or recreating if needed."""
        async with self._ensure_client_lock:
            try:
                running = asyncio.get_running_loop()
            except RuntimeError:
                running = None
            if self._client is not None and self._client_loop is not running:
                with contextlib.suppress(Exception):
                    await self._close_client(self._client)
                self._client = None
                self._client_loop = None
            if self._client is None:
                try:
                    self._client_loop = asyncio.get_running_loop()
                except RuntimeError:
                    self._client_loop = None
                self._client = self._create_client()
            return self._client

    async def _invalidate_client(self) -> None:
        """Close and clear the cached client."""
        async with self._ensure_client_lock:
            if self._client is not None:
                with contextlib.suppress(Exception):
                    await self._close_client(self._client)
                self._client = None
                self._client_loop = None


class HealthCheck(Protocol[T_co]):
    """Base class for health checks."""

    async def __call__(self) -> T_co: ...


class HealthCheckDSN(ToDictMixin, HealthCheck[T_co], Generic[T_co]):
    """Base class for health checks that can be created from a DSN.

    Contract: subclasses must define _allowed_schemes(), _default_name(),
    parse_dsn(), and _from_parsed_dsn(). The check stores its display name in
    _name (used in HealthCheckResult and error reporting). DSN validation uses
    validate_dsn(); fast_healthchecks.dsn NewTypes are typing-only, not runtime.
    """

    @classmethod
    @abstractmethod
    def _allowed_schemes(cls) -> tuple[str, ...]:
        """Return DSN schemes allowed for this check (e.g. ('redis', 'rediss'))."""
        raise NotImplementedError  # pragma: no cover

    @classmethod
    @abstractmethod
    def _default_name(cls) -> str:
        """Return the default check name for from_dsn (e.g. 'Redis')."""
        raise NotImplementedError  # pragma: no cover

    @classmethod
    @abstractmethod
    def parse_dsn(cls, dsn: str) -> object:
        """Parse the DSN string. Subclasses must implement."""
        raise NotImplementedError  # pragma: no cover

    @classmethod
    @abstractmethod
    def _from_parsed_dsn(
        cls,
        parsed: Any,  # noqa: ANN401
        *,
        name: str = "Service",
        timeout: float = DEFAULT_HC_TIMEOUT,
        **kwargs: Any,  # noqa: ANN401
    ) -> HealthCheckDSN[T_co]:
        """Create a check instance from parsed DSN."""
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def from_dsn(
        cls,
        dsn: str,
        *,
        name: str | None = None,
        timeout: float = DEFAULT_HC_TIMEOUT,
        **kwargs: Any,  # noqa: ANN401
    ) -> HealthCheckDSN[T_co]:
        """Create a check instance from a DSN string.

        Returns:
            HealthCheckDSN: Configured check instance.
        """
        if name is None:
            name = cls._default_name()
        dsn = cls.validate_dsn(dsn, allowed_schemes=cls._allowed_schemes())
        parsed = cls.parse_dsn(dsn)
        return cls._from_parsed_dsn(parsed, name=name, timeout=timeout, **kwargs)

    @classmethod
    def validate_dsn(cls, dsn: str, *, allowed_schemes: tuple[str, ...]) -> str:
        """Validate the DSN has an allowed scheme.

        Allows compound schemes (e.g. postgresql+asyncpg) when the base
        part before '+' is in allowed_schemes. Scheme comparison is case-insensitive.

        Returns:
            str: The DSN string (stripped of leading/trailing whitespace).

        Raises:
            TypeError: If dsn is not a string.
            ValueError: If DSN is empty or scheme is not in allowed_schemes.
        """
        if not isinstance(dsn, str):
            msg = f"DSN must be str, got {type(dsn).__name__!r}"
            raise TypeError(msg) from None

        dsn = dsn.strip()
        if not dsn:
            msg = "DSN cannot be empty"
            raise ValueError(msg) from None

        if not allowed_schemes:
            msg = "allowed_schemes cannot be empty"
            raise ValueError(msg) from None

        parsed = urlsplit(dsn)
        scheme = (parsed.scheme or "").lower()
        base_scheme = scheme.split("+", 1)[0] if "+" in scheme else scheme

        allowed_set = frozenset(s.lower() for s in allowed_schemes)
        if scheme not in allowed_set and base_scheme not in allowed_set:
            schemes_str = ", ".join(sorted(allowed_set))
            msg = f"DSN scheme must be one of {schemes_str} (or compound e.g. postgresql+driver), got {scheme!r}"
            raise ValueError(msg) from None

        return dsn
