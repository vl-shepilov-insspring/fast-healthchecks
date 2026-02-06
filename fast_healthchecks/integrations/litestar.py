"""Litestar integration for health checks."""

from __future__ import annotations

from collections.abc import Iterable
from http import HTTPStatus

from litestar import Response, get
from litestar.handlers.http_handlers import HTTPRouteHandler

from fast_healthchecks.integrations.base import (
    HandlerType,
    Probe,
    ProbeRouteOptions,
    build_health_routes,
    create_probe_route_handler,
    default_handler,
    healthcheck_shutdown,
    probe_route_path,
)

__all__ = ["health", "healthcheck_shutdown"]


def _add_probe_route(probe: Probe, options: ProbeRouteOptions) -> HTTPRouteHandler:
    params = options.to_route_params()
    handle_request = create_probe_route_handler(
        probe,
        params,
        response_factory=lambda c, h, s: Response(content=c, headers=h, status_code=s),
    )

    @get(
        path=probe_route_path(probe, options.prefix),
        name=probe.name,
        operation_id=f"health:{probe.name}",
        summary=probe.endpoint_summary,
        include_in_schema=options.debug,
    )
    async def route_handler() -> Response[bytes]:
        return await handle_request()

    return route_handler


def health(  # noqa: PLR0913
    *probes: Probe,
    success_handler: HandlerType = default_handler,
    failure_handler: HandlerType = default_handler,
    success_status: int = HTTPStatus.NO_CONTENT,
    failure_status: int = HTTPStatus.SERVICE_UNAVAILABLE,
    debug: bool = False,
    prefix: str = "/health",
    timeout: float | None = None,
    options: ProbeRouteOptions | None = None,
) -> Iterable[HTTPRouteHandler]:
    """Make list of routes for healthchecks.

    Returns:
        Iterable[HTTPRouteHandler]: Generated healthcheck route handlers.

    To close health check resources on app shutdown, pass the same probes
    to ``healthcheck_shutdown(probes)`` and add the returned callback to
    Litestar's ``on_shutdown`` list.
    """
    return build_health_routes(
        probes,
        add_route=_add_probe_route,
        success_handler=success_handler,
        failure_handler=failure_handler,
        success_status=success_status,
        failure_status=failure_status,
        debug=debug,
        prefix=prefix,
        timeout=timeout,
        options=options,
    )
