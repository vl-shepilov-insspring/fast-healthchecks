"""Integration tests for FastAPI HealthcheckRouter with real backends."""

import json

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from examples.fastapi_example.main import app_custom, app_fail, app_integration

pytestmark = pytest.mark.integration


def test_liveness_probe() -> None:
    """Liveness probe returns success when checks pass."""
    with TestClient(app_integration) as client:
        response = client.get("/health/liveness")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""


def test_readiness_probe() -> None:
    """Readiness probe returns success when all checks pass."""
    with TestClient(app_integration) as client:
        response = client.get("/health/readiness")
        assert response.status_code == status.HTTP_204_NO_CONTENT, (
            f"readiness returned {response.status_code}; body={response.text!r}"
        )
        assert response.content == b""


def test_startup_probe() -> None:
    """Startup probe returns success when checks pass."""
    with TestClient(app_integration) as client:
        response = client.get("/health/startup")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""


def test_readiness_probe_fail() -> None:
    """Readiness probe returns failure when a check fails."""
    with TestClient(app_fail) as client:
        response = client.get("/health/readiness")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        # With debug=True the body is the full report (results, allow_partial_failure); otherwise minimal {"status": "unhealthy"}
        assert data.get("status") == "unhealthy" or (
            "results" in data and any(not r.get("healthy", True) for r in data["results"])
        )


def test_custom_handler() -> None:
    """Custom handler is used for probe response."""
    with TestClient(app_custom) as client:
        response = client.get("/custom_health/readiness")
    assert response.status_code == status.HTTP_200_OK
    assert response.content == json.dumps(
        {"results": [{"name": "Async dummy", "healthy": True, "error_details": None}], "allow_partial_failure": False},
        ensure_ascii=False,
        allow_nan=False,
        indent=None,
        separators=(",", ":"),
    ).encode("utf-8")
