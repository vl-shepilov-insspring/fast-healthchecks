import json

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT, HTTP_503_SERVICE_UNAVAILABLE
from litestar.testing import TestClient

from examples.litestar_example.main import app_custom, app_fail, app_integration

app_integration.debug = True
pytestmark = pytest.mark.integration


def test_liveness_probe() -> None:
    with TestClient(app=app_integration) as client:
        response = client.get("/health/liveness")
        assert response.status_code == HTTP_204_NO_CONTENT
        assert response.content == b""


def test_readiness_probe() -> None:
    with TestClient(app=app_integration) as client:
        response = client.get("/health/readiness")
        assert response.status_code == HTTP_204_NO_CONTENT, (
            f"readiness returned {response.status_code}; body={response.text!r}"
        )
        assert response.content == b""


def test_startup_probe() -> None:
    with TestClient(app=app_integration) as client:
        response = client.get("/health/startup")
        assert response.status_code == HTTP_204_NO_CONTENT
        assert response.content == b""


def test_readiness_probe_fail() -> None:
    with TestClient(app=app_fail) as client:
        response = client.get("/health/readiness")
        assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        # With debug=True the body is the full report (results, allow_partial_failure); otherwise minimal {"status": "unhealthy"}
        assert data.get("status") == "unhealthy" or (
            "results" in data and any(not r.get("healthy", True) for r in data["results"])
        )


def test_custom_handler() -> None:
    with TestClient(app=app_custom) as client:
        response = client.get("/custom_health/readiness")
        assert response.status_code == HTTP_200_OK
    assert response.content == json.dumps(
        {"results": [{"name": "Async dummy", "healthy": True, "error_details": None}], "allow_partial_failure": False},
        ensure_ascii=False,
        allow_nan=False,
        indent=None,
        separators=(",", ":"),
    ).encode("utf-8")
