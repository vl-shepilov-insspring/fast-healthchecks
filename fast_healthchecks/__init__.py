"""Framework-agnostic health checks for ASGI apps (FastAPI, FastStream, Litestar).

Optional backends and framework integrations are available as install extras.
See the project's pyproject.toml for extra names (e.g. asyncpg, redis, fastapi).
"""

from fast_healthchecks.checks import FunctionConfig
from fast_healthchecks.checks.types import Check
from fast_healthchecks.integrations.base import Probe, healthcheck_shutdown, run_probe
from fast_healthchecks.models import (
    HealthCheckError,
    HealthCheckReport,
    HealthCheckResult,
    HealthCheckSSRFError,
    HealthCheckTimeoutError,
)

__version__ = "0.2.4"

__all__ = (
    "Check",
    "FunctionConfig",
    "HealthCheckError",
    "HealthCheckReport",
    "HealthCheckResult",
    "HealthCheckSSRFError",
    "HealthCheckTimeoutError",
    "Probe",
    "__version__",
    "healthcheck_shutdown",
    "run_probe",
)
