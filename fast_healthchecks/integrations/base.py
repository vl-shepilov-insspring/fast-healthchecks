"""Base classes for integrations."""

from __future__ import annotations

import asyncio
import contextlib
import json
import re
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import asdict
from http import HTTPStatus
from typing import Any, NamedTuple, TypeAlias, TypeVar

from fast_healthchecks.checks._base import result_on_error
from fast_healthchecks.checks.types import Check
from fast_healthchecks.models import HealthCheckReport, HealthCheckResult

HandlerType: TypeAlias = Callable[..., Awaitable[dict[str, Any] | None]]

OnCheckStart: TypeAlias = Callable[[Check, int], Awaitable[None]]
OnCheckEnd: TypeAlias = Callable[[Check, int, HealthCheckResult], Awaitable[None]]


class ProbeRouteParams(NamedTuple):
    """Parameters for probe route handlers. Used by framework integrations."""

    success_handler: HandlerType
    failure_handler: HandlerType
    success_status: int
    failure_status: int
    debug: bool
    timeout: float | None

    def to_options(self, prefix: str = "/health") -> ProbeRouteOptions:
        """Return ProbeRouteOptions with the given prefix."""
        return ProbeRouteOptions(
            success_handler=self.success_handler,
            failure_handler=self.failure_handler,
            success_status=self.success_status,
            failure_status=self.failure_status,
            debug=self.debug,
            timeout=self.timeout,
            prefix=prefix,
        )


class ProbeRouteOptions(NamedTuple):
    """Options for probe routes. Combines handler params and path prefix."""

    success_handler: HandlerType
    failure_handler: HandlerType
    success_status: int
    failure_status: int
    debug: bool
    timeout: float | None
    prefix: str

    def to_route_params(self) -> ProbeRouteParams:
        """Return ProbeRouteParams for create_probe_route_handler."""
        return ProbeRouteParams(
            success_handler=self.success_handler,
            failure_handler=self.failure_handler,
            success_status=self.success_status,
            failure_status=self.failure_status,
            debug=self.debug,
            timeout=self.timeout,
        )


class Probe(NamedTuple):
    """A probe is a collection of health checks that can be run together.

    Attributes:
        name: The name of the probe.
        checks: A sequence of health checks to run.
        summary: A summary of the probe. If not provided, a default summary will be generated.
        allow_partial_failure: If True, probe is healthy when at least one check passes.
    """

    name: str
    checks: Sequence[Check]
    summary: str | None = None
    allow_partial_failure: bool = False

    @property
    def endpoint_summary(self) -> str:
        """Return a summary for the endpoint.

        If a summary is provided, it will be used. Otherwise, a default summary will be generated.
        """
        if self.summary:
            return self.summary
        title = re.sub(
            pattern=r"[^a-z0-9]+",
            repl=" ",
            string=self.name.lower().capitalize(),
            flags=re.IGNORECASE,
        )
        return f"{title} probe"


class ProbeAsgiResponse(NamedTuple):
    """A response from an ASGI probe.

    Attributes:
        data: The response data (healthcheck results).
        healthy: Whether all healthchecks passed.
    """

    data: dict[str, Any]
    healthy: bool


async def default_handler(response: ProbeAsgiResponse) -> dict[str, Any] | None:
    """Default handler for health check route.

    Returns a minimal body ``{"status": "healthy"|"unhealthy"}`` for responses
    that require content (e.g. 503). Returns ``None`` for 204 No Content.

    Args:
        response: The response from the probe.

    Returns:
        Minimal status dict, or None for no response body.
    """
    await asyncio.sleep(0)
    return {"status": "healthy" if response.healthy else "unhealthy"}


def build_probe_route_options(  # noqa: PLR0913
    *,
    success_handler: HandlerType = default_handler,
    failure_handler: HandlerType = default_handler,
    success_status: int = HTTPStatus.NO_CONTENT,
    failure_status: int = HTTPStatus.SERVICE_UNAVAILABLE,
    debug: bool = False,
    prefix: str = "/health",
    timeout: float | None = None,
) -> ProbeRouteOptions:
    """Build ProbeRouteOptions with defaults. Used by health() and _add_probe_route.

    Returns:
        ProbeRouteOptions: Options for probe routes.
    """
    return ProbeRouteOptions(
        success_handler=success_handler,
        failure_handler=failure_handler,
        success_status=success_status,
        failure_status=failure_status,
        debug=debug,
        timeout=timeout,
        prefix=prefix,
    )


def _get_check_name(check: Check, index: int) -> str:
    return getattr(check, "name", None) or getattr(check, "_name", f"Check-{index}")


async def _run_check_safe(check: Check, index: int) -> HealthCheckResult:
    try:
        return await check()
    except Exception:  # noqa: BLE001
        return result_on_error(_get_check_name(check, index))


async def _gather_check_results(
    probe: Probe,
    timeout: float | None = None,
    *,
    on_timeout_return_failure: bool = False,
) -> list[HealthCheckResult]:
    """Run all probe checks in parallel, optionally with timeout.

    Args:
        probe: The probe whose checks to run.
        timeout: Max seconds. When exceeded, raises TimeoutError unless
            on_timeout_return_failure is True.
        on_timeout_return_failure: If True, return failure results instead of raising.

    Returns:
        List of HealthCheckResult from each check.

    Raises:
        TimeoutError: When timeout is exceeded and on_timeout_return_failure is False.
    """
    tasks = [_run_check_safe(check, i) for i, check in enumerate(probe.checks)]
    if timeout is not None:
        try:
            return list(
                await asyncio.wait_for(asyncio.gather(*tasks), timeout=timeout),
            )
        except asyncio.TimeoutError:
            if on_timeout_return_failure:
                return [
                    HealthCheckResult(
                        name=_get_check_name(check, i),
                        healthy=False,
                        error_details="Probe timed out",
                    )
                    for i, check in enumerate(probe.checks)
                ]
            raise
    return list(await asyncio.gather(*tasks))


class ProbeAsgi:
    """An ASGI probe.

    Args:
        probe: The probe to run.
        options: Route options. When None, built from remaining kwargs.
        success_handler: The handler to use for successful responses.
        failure_handler: The handler to use for failed responses.
        success_status: The status code to use for successful responses.
        failure_status: The status code to use for failed responses.
        debug: Whether to include debug information in the response.
        timeout: Maximum seconds for all checks. When exceeded, returns a
            failure response.
    """

    __slots__ = (
        "_debug",
        "_exclude_fields",
        "_failure_handler",
        "_failure_status",
        "_map_handler",
        "_map_status",
        "_probe",
        "_success_handler",
        "_success_status",
        "_timeout",
    )

    _probe: Probe
    _success_handler: HandlerType
    _failure_handler: HandlerType
    _success_status: int
    _failure_status: int
    _debug: bool
    _exclude_fields: set[str]
    _map_status: dict[bool, int]
    _map_handler: dict[bool, HandlerType]
    _timeout: float | None

    def __init__(  # noqa: PLR0913
        self,
        probe: Probe,
        *,
        options: ProbeRouteOptions | None = None,
        success_handler: HandlerType = default_handler,
        failure_handler: HandlerType = default_handler,
        success_status: int = HTTPStatus.NO_CONTENT,
        failure_status: int = HTTPStatus.SERVICE_UNAVAILABLE,
        debug: bool = False,
        timeout: float | None = None,
    ) -> None:
        """Initialize the ASGI probe."""
        if options is None:
            options = build_probe_route_options(
                success_handler=success_handler,
                failure_handler=failure_handler,
                success_status=success_status,
                failure_status=failure_status,
                debug=debug,
                timeout=timeout,
            )
        params = options.to_route_params()
        self._probe = probe
        self._success_handler = params.success_handler
        self._failure_handler = params.failure_handler
        self._success_status = params.success_status
        self._failure_status = params.failure_status
        self._debug = params.debug
        self._timeout = params.timeout
        self._exclude_fields = {"allow_partial_failure", "error_details"} if not params.debug else set()
        self._map_status = {True: params.success_status, False: params.failure_status}
        self._map_handler = {True: params.success_handler, False: params.failure_handler}

    async def __call__(self) -> tuple[bytes, dict[str, str] | None, int]:
        """Run the probe.

        Returns:
            A tuple containing the response body, headers, and status code.
        """
        results = await _gather_check_results(
            self._probe,
            timeout=self._timeout,
            on_timeout_return_failure=True,
        )
        report = HealthCheckReport(
            results=results,
            allow_partial_failure=self._probe.allow_partial_failure,
        )
        response = ProbeAsgiResponse(
            data=asdict(
                report,
                dict_factory=lambda x: {k: v for (k, v) in x if k not in self._exclude_fields},
            ),
            healthy=report.healthy,
        )

        actual_status = self._map_status[response.healthy]
        content_needed = actual_status not in {
            HTTPStatus.NO_CONTENT,
            HTTPStatus.NOT_MODIFIED,
        } and not (response.healthy and actual_status < HTTPStatus.OK)

        content = b""
        headers = None
        if content_needed:
            # When debug=True and unhealthy, return full report so assertion/logs show which check failed
            if self._debug and not response.healthy:
                content_ = response.data
            else:
                handler = self._map_handler[response.healthy]
                content_ = await handler(response)
            if content_ is not None:
                content = json.dumps(
                    content_,
                    ensure_ascii=False,
                    allow_nan=False,
                    indent=None,
                    separators=(",", ":"),
                ).encode("utf-8")
                headers = {
                    "content-type": "application/json",
                    "content-length": str(len(content)),
                }

        return content, headers, self._map_status[response.healthy]


def make_probe_asgi(  # noqa: PLR0913
    probe: Probe,
    *,
    options: ProbeRouteOptions | None = None,
    success_handler: HandlerType = default_handler,
    failure_handler: HandlerType = default_handler,
    success_status: int = HTTPStatus.NO_CONTENT,
    failure_status: int = HTTPStatus.SERVICE_UNAVAILABLE,
    debug: bool = False,
    timeout: float | None = None,
) -> Callable[[], Awaitable[tuple[bytes, dict[str, str] | None, int]]]:
    """Create an ASGI probe from a probe.

    Args:
        probe: The probe to create the ASGI probe from.
        options: Route options. When None, built from remaining kwargs.
        success_handler: The handler to use for successful responses.
        failure_handler: The handler to use for failed responses.
        success_status: The status code to use for successful responses.
        failure_status: The status code to use for failed responses.
        debug: Whether to include debug information in the response.
        timeout: Maximum seconds for all checks. When exceeded, returns a
            failure response with "Probe timed out" for each check.

    Returns:
        An ASGI probe.
    """
    return ProbeAsgi(
        probe,
        options=options,
        success_handler=success_handler,
        failure_handler=failure_handler,
        success_status=success_status,
        failure_status=failure_status,
        debug=debug,
        timeout=timeout,
    )


def probe_path_suffix(probe: Probe) -> str:
    """Return the path suffix for a probe (name without leading slash)."""
    return probe.name.removeprefix("/")


def probe_route_path(probe: Probe, prefix: str = "/health") -> str:
    """Return the route path for a probe given a prefix."""
    return f"{prefix.removesuffix('/')}/{probe_path_suffix(probe)}"


_T = TypeVar("_T")


def _build_health_routes(
    probes: Iterable[Probe],
    *,
    add_route: Callable[[Probe, ProbeRouteOptions], _T],
    options: ProbeRouteOptions,
) -> list[_T]:
    """Build health route entries for each probe using the given add_route callback.

    Returns:
        list[_T]: List of route entries produced by add_route for each probe.
    """
    return [add_route(probe, options) for probe in probes]


def build_health_routes(  # noqa: PLR0913
    probes: Iterable[Probe],
    add_route: Callable[[Probe, ProbeRouteOptions], _T],
    *,
    success_handler: HandlerType = default_handler,
    failure_handler: HandlerType = default_handler,
    success_status: int = HTTPStatus.NO_CONTENT,
    failure_status: int = HTTPStatus.SERVICE_UNAVAILABLE,
    debug: bool = False,
    prefix: str = "/health",
    timeout: float | None = None,
    options: ProbeRouteOptions | None = None,
) -> list[_T]:
    """Build health route entries for framework integrations.

    Used by Litestar and FastStream health() functions. Builds options from
    kwargs when options is None, then delegates to _build_health_routes.

    Returns:
        list[_T]: List of route entries produced by add_route for each probe.
    """
    if options is None:
        options = build_probe_route_options(
            success_handler=success_handler,
            failure_handler=failure_handler,
            success_status=success_status,
            failure_status=failure_status,
            debug=debug,
            prefix=prefix,
            timeout=timeout,
        )
    return _build_health_routes(probes, add_route=add_route, options=options)


def create_probe_route_handler(
    probe: Probe,
    params: ProbeRouteParams,
    *,
    response_factory: Callable[[bytes, dict[str, str], int], _T],
) -> Callable[[], Awaitable[_T]]:
    """Create an async handler for a probe route.

    Framework integrations use this with their response_factory to build
    the handler, then register it (FastAPI add_api_route, FastStream/Litestar return).

    Returns:
        Async callable that runs the probe and returns the framework response.
    """
    probe_asgi = make_probe_asgi(probe, options=params.to_options())

    async def handler() -> _T:
        content, headers, status_code = await probe_asgi()
        return response_factory(content, headers or {}, status_code)

    return handler


async def run_probe(
    probe: Probe,
    *,
    timeout: float | None = None,
    on_check_start: OnCheckStart | None = None,
    on_check_end: OnCheckEnd | None = None,
) -> HealthCheckReport:
    """Run a probe and return the health check report.

    Can be used without ASGI (CLI, cron, tests).

    When ``on_check_start`` or ``on_check_end`` are provided, checks run
    sequentially (for ordering guarantees). Otherwise they run in parallel.

    Args:
        probe: The probe to run.
        timeout: Maximum seconds for all checks. Raises asyncio.TimeoutError if exceeded.
        on_check_start: Optional callback before each check runs. Receives (check, index).
        on_check_end: Optional callback after each check completes. Receives (check, index, result).

    Returns:
        HealthCheckReport with results from all checks.
    """
    if on_check_start is None and on_check_end is None:
        results = await _gather_check_results(probe, timeout=timeout)
    else:

        async def _run_with_hooks() -> list[HealthCheckResult]:
            out: list[HealthCheckResult] = []
            for i, check in enumerate(probe.checks):
                if on_check_start is not None:
                    await on_check_start(check, i)
                result = await _run_check_safe(check, i)
                if on_check_end is not None:
                    await on_check_end(check, i, result)
                out.append(result)
            return out

        if timeout is not None:
            results = await asyncio.wait_for(_run_with_hooks(), timeout=timeout)
        else:
            results = await _run_with_hooks()

    return HealthCheckReport(
        results=results,
        allow_partial_failure=probe.allow_partial_failure,
    )


async def close_probes(probes: Iterable[Probe]) -> None:
    """Close resources owned by checks in the given probes.

    Calls ``aclose()`` on each check that has it (e.g. checks with cached
    clients). Ignores exceptions so one failure does not block others.

    Args:
        probes: Probes whose checks should be closed.
    """
    for probe in probes:
        for check in probe.checks:
            aclose = getattr(check, "aclose", None)
            if callable(aclose):
                with contextlib.suppress(Exception):
                    await aclose()


def healthcheck_shutdown(probes: Iterable[Probe]) -> Callable[[], Awaitable[None]]:
    """Return an async shutdown callback that closes the given probes' checks.

    Use this with framework lifespan/shutdown hooks (e.g. Litestar ``on_shutdown``,
    FastStream shutdown) so that health check resources are closed on app shutdown.

    Args:
        probes: The same probes passed to your health routes.

    Returns:
        An async callable with no arguments that closes all checks with ``aclose()``.
    """

    async def _shutdown() -> None:
        await close_probes(probes)

    return _shutdown
