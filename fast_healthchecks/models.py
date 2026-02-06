"""Models for healthchecks."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

__all__ = (
    "HealthCheckError",
    "HealthCheckReport",
    "HealthCheckResult",
    "HealthCheckSSRFError",
    "HealthCheckTimeoutError",
)


class HealthCheckError(Exception):
    """Base exception for health-check-related failures.

    Raised or used as a base for timeouts, SSRF validation, and other
    health-check errors. Subclasses preserve the original exception type
    (e.g. HealthCheckTimeoutError is also an asyncio.TimeoutError) so
    existing code that catches TimeoutError or ValueError continues to work.
    """


class HealthCheckTimeoutError(HealthCheckError, asyncio.TimeoutError):
    """Raised when a probe or check run exceeds its timeout.

    Subclass of both HealthCheckError and asyncio.TimeoutError so that
    ``except asyncio.TimeoutError`` or ``except TimeoutError`` still catch it.
    """


class HealthCheckSSRFError(HealthCheckError, ValueError):
    """Raised when URL or host validation fails (SSRF / block_private_hosts).

    Subclass of both HealthCheckError and ValueError so that
    ``except ValueError`` still catches it.
    """


@dataclass(frozen=True)
class HealthCheckResult:
    """Result of a healthcheck.

    Attributes:
        name: Name of the healthcheck.
        healthy: Whether the healthcheck passed.
        error_details: Details of the error if the healthcheck failed.
    """

    name: str
    healthy: bool
    error_details: str | None = None

    def __str__(self) -> str:
        """Return a string representation of the result."""
        return f"{self.name}: {'healthy' if self.healthy else 'unhealthy'}"


@dataclass(frozen=True)
class HealthCheckReport:
    """Report of healthchecks.

    Attributes:
        results: List of healthcheck results.
        allow_partial_failure: If True, report is healthy when at least one check passes.
    """

    results: list[HealthCheckResult]
    allow_partial_failure: bool = False

    def __str__(self) -> str:
        """Return a string representation of the report."""
        return "\n".join(str(result) for result in self.results)

    @property
    def healthy(self) -> bool:
        """Return whether all healthchecks passed (or allowed partial failure)."""
        if self.allow_partial_failure:
            return any(result.healthy for result in self.results)
        return all(result.healthy for result in self.results)
