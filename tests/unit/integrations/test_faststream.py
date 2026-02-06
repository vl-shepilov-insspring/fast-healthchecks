"""Unit tests for FastStream health() and probes.

Uses FastStream's TestKafkaBroker(connect_only=True) and TestApp so tests run
without a real Kafka. See: https://faststream.ag2.ai/latest/getting-started/lifespan/test/
"""

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import cast

import httpx
import pytest
from faststream import TestApp
from faststream.asgi import AsgiFastStream
from faststream.kafka import KafkaBroker, TestKafkaBroker

from examples.faststream_example.main import app_custom, app_fail, app_success, broker
from fast_healthchecks.integrations.base import Probe
from fast_healthchecks.integrations.faststream import health

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@asynccontextmanager
async def _faststream_client(app: AsgiFastStream) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Run app under TestKafkaBroker(connect_only=True) + TestApp and yield an HTTP client.

    Per FastStream testing docs: patch broker first, then app lifespan.

    Yields:
        httpx.AsyncClient: Client bound to the app (ASGITransport, base_url=http://test).
    """
    kafka_broker = cast("KafkaBroker", app.broker)
    async with (
        TestKafkaBroker(kafka_broker, connect_only=True),
        TestApp(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client,
    ):
        yield client


async def test_health_without_options_uses_defaults() -> None:
    """health(probe) without options uses build_probe_route_options() defaults."""
    routes = health(Probe(name="liveness", checks=[]))
    app = AsgiFastStream(broker, asgi_routes=list(routes))
    async with _faststream_client(app) as client:
        response = await client.get("/health/liveness")
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b""


async def test_liveness_probe() -> None:
    """Liveness probe returns success when checks pass."""
    async with _faststream_client(app_success) as client:
        response = await client.get("/health/liveness")
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b""


async def test_readiness_probe() -> None:
    """Readiness probe returns success when all checks pass."""
    async with _faststream_client(app_success) as client:
        response = await client.get("/health/readiness")
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b""


async def test_startup_probe() -> None:
    """Startup probe returns success when checks pass."""
    async with _faststream_client(app_success) as client:
        response = await client.get("/health/startup")
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b""


async def test_readiness_probe_fail() -> None:
    """Readiness probe returns failure when a check fails."""
    async with _faststream_client(app_fail) as client:
        response = await client.get("/health/readiness")
    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    data = response.json()
    assert data.get("status") == "unhealthy" or (
        "results" in data and any(not r.get("healthy", True) for r in data["results"])
    )


async def test_custom_handler() -> None:
    """Custom handler is used for probe response."""
    async with _faststream_client(app_custom) as client:
        response = await client.get("/custom_health/readiness")
    assert response.status_code == HTTPStatus.OK
    assert response.content == json.dumps(
        {"results": [{"name": "Async dummy", "healthy": True, "error_details": None}], "allow_partial_failure": False},
        ensure_ascii=False,
        allow_nan=False,
        indent=None,
        separators=(",", ":"),
    ).encode("utf-8")
