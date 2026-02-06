"""FastStream integration for health checks."""

from __future__ import annotations

from collections.abc import Iterable
from http import HTTPStatus
from typing import TYPE_CHECKING

from faststream.asgi.handlers import get
from faststream.asgi.response import AsgiResponse
from faststream.asgi.types import Scope
from faststream.specification.schema.extra.tag import Tag

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

if TYPE_CHECKING:
    from faststream.asgi.types import ASGIApp

__all__ = ["health", "healthcheck_shutdown"]


def _add_probe_route(probe: Probe, options: ProbeRouteOptions) -> tuple[str, ASGIApp]:
    params = options.to_route_params()
    handler_impl = create_probe_route_handler(
        probe,
        params,
        response_factory=lambda c, h, s: AsgiResponse(c, s, headers=h),
    )

    @get(
        include_in_schema=options.debug,
        description=probe.endpoint_summary,
        tags=[Tag(name="Healthchecks")] if options.debug else None,
        unique_id=f"health:{probe.name}",
    )
    async def handle_request(_scope: Scope) -> AsgiResponse:
        return await handler_impl()

    return probe_route_path(probe, options.prefix), handle_request


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
) -> Iterable[tuple[str, ASGIApp]]:
    """Make list of routes for healthchecks.

    Returns:
        Iterable[tuple[str, ASGIApp]]: Generated healthcheck routes.

    To close health check resources on app shutdown, pass the same probes
    to ``healthcheck_shutdown(probes)`` and register the returned callback
    with your FastStream app's shutdown hooks (e.g. ``@app.on_shutdown``).
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
