"""FastStream integration for health checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from faststream.asgi.handlers import get
from faststream.asgi.response import AsgiResponse
from faststream.specification.schema.extra.tag import Tag

from fast_healthchecks.integrations.base import (
    Probe,
    ProbeRouteOptions,
    build_health_routes,
    create_probe_route_handler,
    healthcheck_shutdown,
    probe_route_path,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from faststream.asgi.types import ASGIApp, Scope

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


def health(
    *probes: Probe,
    options: ProbeRouteOptions | None = None,
) -> Iterable[tuple[str, ASGIApp]]:
    """Make list of routes for healthchecks.

    Returns:
        Iterable[tuple[str, ASGIApp]]: Generated healthcheck routes.

    To close health check resources on app shutdown, pass the same probes
    to ``healthcheck_shutdown(probes)`` and register the returned callback
    with your FastStream app's shutdown hooks (e.g. ``@app.on_shutdown``).
    """
    return build_health_routes(probes, add_route=_add_probe_route, options=options)
