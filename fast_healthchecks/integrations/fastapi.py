"""FastAPI integration for health checks."""

from __future__ import annotations

from http import HTTPStatus

from fastapi import APIRouter
from fastapi.responses import Response

from fast_healthchecks.integrations.base import (
    HandlerType,
    Probe,
    ProbeRouteOptions,
    build_probe_route_options,
    close_probes,
    create_probe_route_handler,
    default_handler,
    healthcheck_shutdown,
    probe_path_suffix,
)

__all__ = ["HealthcheckRouter", "healthcheck_shutdown"]


class HealthcheckRouter(APIRouter):
    """A router for health checks.

    Args:
        probes: An iterable of probes to run.
        debug: Whether to include the probes in the schema. Defaults to False.

    To close health check resources (e.g. cached clients) on app shutdown,
    call ``await router.close()`` from your FastAPI lifespan, or use
    ``healthcheck_shutdown(probes)`` and call the returned callback.
    """

    def __init__(  # noqa: PLR0913
        self,
        *probes: Probe,
        success_handler: HandlerType = default_handler,
        failure_handler: HandlerType = default_handler,
        success_status: int = HTTPStatus.NO_CONTENT,
        failure_status: int = HTTPStatus.SERVICE_UNAVAILABLE,
        debug: bool = False,
        prefix: str = "/health",
        timeout: float | None = None,
        options: ProbeRouteOptions | None = None,
    ) -> None:
        """Initialize the router."""
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
        super().__init__(prefix=options.prefix.removesuffix("/"), tags=["Healthchecks"])
        self._healthcheck_probes: list[Probe] = list(probes)
        for probe in probes:
            self._add_probe_route(probe, options=options)

    def _add_probe_route(self, probe: Probe, *, options: ProbeRouteOptions) -> None:
        params = options.to_route_params()
        handle_request = create_probe_route_handler(
            probe,
            params,
            response_factory=lambda c, h, s: Response(content=c, status_code=s, headers=h),
        )

        self.add_api_route(
            path=f"/{probe_path_suffix(probe)}",
            endpoint=handle_request,
            status_code=options.success_status,
            summary=probe.endpoint_summary,
            include_in_schema=options.debug,
            response_model=None,
            response_class=Response,
        )

    async def close(self) -> None:
        """Close resources owned by this router's health check probes.

        Call this from your FastAPI lifespan shutdown (e.g. after ``yield``
        in an ``@asynccontextmanager`` lifespan) so cached clients are closed.
        """
        await close_probes(self._healthcheck_probes)
