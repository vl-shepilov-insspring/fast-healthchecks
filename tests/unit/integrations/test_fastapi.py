import json

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from examples.fastapi_example.main import app_custom, app_fail, app_success
from examples.probes import READINESS_CHECKS_SUCCESS
from fast_healthchecks.integrations.base import Probe, default_handler
from fast_healthchecks.integrations.fastapi import HealthcheckRouter

from .helpers import CheckWithAclose

pytestmark = pytest.mark.unit

client = TestClient(app_success)


def _success_check() -> bool:
    return True


def test_liveness_probe() -> None:
    response = client.get("/health/liveness")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""


def test_readiness_probe() -> None:
    response = client.get("/health/readiness")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""


def test_startup_probe() -> None:
    response = client.get("/health/startup")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""


def test_readiness_probe_fail() -> None:
    client_fail = TestClient(app_fail)
    response = client_fail.get("/health/readiness")
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    data = response.json()
    # With debug=True the body is the full report (results, allow_partial_failure); otherwise minimal {"status": "unhealthy"}
    assert data.get("status") == "unhealthy" or (
        "results" in data and any(not r.get("healthy", True) for r in data["results"])
    )


def test_custom_handler() -> None:
    client_custom = TestClient(app_custom)
    response = client_custom.get("/custom_health/readiness")
    assert response.status_code == status.HTTP_200_OK
    assert response.content == json.dumps(
        {"results": [{"name": "Async dummy", "healthy": True, "error_details": None}], "allow_partial_failure": False},
        ensure_ascii=False,
        allow_nan=False,
        indent=None,
        separators=(",", ":"),
    ).encode("utf-8")


def test_default_handler_returns_minimal_body() -> None:
    """Test that default_handler returns minimal status body."""
    app = FastAPI()
    app.include_router(
        HealthcheckRouter(
            Probe(name="readiness", checks=READINESS_CHECKS_SUCCESS),
            success_handler=default_handler,
            failure_handler=default_handler,
            success_status=status.HTTP_200_OK,
            failure_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            debug=True,
            prefix="/health",
        ),
    )
    client_default = TestClient(app)
    response = client_default.get("/health/readiness")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_router_close_closes_probe_checks() -> None:
    """HealthcheckRouter.close() calls aclose() on checks that have it."""
    check = CheckWithAclose(name="A")
    probe = Probe(name="readiness", checks=[check])
    router = HealthcheckRouter(probe, prefix="/health")
    await router.close()
    check._aclose_mock.assert_awaited_once_with()
