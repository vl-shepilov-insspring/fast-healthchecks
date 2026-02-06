from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

import pytest
from dotenv import dotenv_values

# Set Windows event loop policy at import so it applies before any test runs.
# TestClient runs the ASGI app in a background thread; that thread creates an
# event loop using the process default policy. Sync integration tests do not
# request the event_loop_policy fixture, so without this, Windows would use
# ProactorEventLoop and psycopg async would raise (readiness probe 503).
# WindowsSelectorEventLoopPolicy is deprecated in 3.14 and removed in 3.16.
if sys.platform == "win32" and sys.version_info < (3, 14):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(scope="session")
def event_loop_policy() -> asyncio.AbstractEventLoopPolicy | None:
    """Use SelectorEventLoop on Windows so psycopg (and other libs) work in async mode.

    Windows defaults to ProactorEventLoop, which psycopg cannot use for async I/O.
    On Python 3.14+, policy APIs are deprecated; return None so pytest-asyncio uses default.
    WindowsSelectorEventLoopPolicy is deprecated in 3.14 and removed in 3.16.

    Returns:
        Event loop policy, or None on Python 3.14+ to avoid calling deprecated APIs.
    """
    if sys.platform == "win32" and sys.version_info < (3, 14):
        return asyncio.WindowsSelectorEventLoopPolicy()
    if sys.version_info >= (3, 14):
        return None
    return asyncio.DefaultEventLoopPolicy()


def _service_config_from_env(
    env_config: dict[str, Any],
    service: str,
    defaults: dict[str, Any],
    *,
    int_keys: frozenset[str] = frozenset(),
    list_keys: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Merge env overrides onto defaults for service config fixtures.

    Returns:
        Config dict with env values overriding defaults for specified keys.
    """
    result = dict(defaults)
    for key in defaults:
        val = env_config.get(f"{service}_{key}".upper())
        if val is not None:
            if key in int_keys:
                result[key] = int(val)
            elif key in list_keys:
                result[key] = [v.strip() for v in str(val).split(",")]
            else:
                result[key] = str(val)
    return result


def pytest_configure(config: pytest.Config) -> None:
    """Ignore unraisable warnings from health-check clients not closed at TestClient teardown.

    When using xdist or multiple test runs, cached clients (aiohttp, OpenSearch, etc.)
    can be GC'd after their event loop is closed, triggering ResourceWarning in __del__.
    TestClient does not expose a shutdown hook to call aclose() on checks.
    """
    config.addinivalue_line(
        "filterwarnings",
        "ignore:Exception ignored in:pytest.PytestUnraisableExceptionWarning",
    )


@pytest.fixture(scope="session", name="env_config")
def fixture_env_config() -> dict[str, Any]:
    return {
        **dotenv_values(".env"),  # load shared default test environment variables
        **os.environ,  # override loaded values with environment variables
    }


# --- Service config fixtures (env-based, reused across integration checks) ---

REDIS_DEFAULTS: dict[str, Any] = {
    "host": "localhost",
    "port": 6379,
    "user": None,
    "password": None,
    "database": 0,
}


@pytest.fixture(scope="session", name="redis_config")
def fixture_redis_config(env_config: dict[str, Any]) -> dict[str, Any]:
    return _service_config_from_env(
        env_config,
        "REDIS",
        REDIS_DEFAULTS,
        int_keys=frozenset({"port", "database"}),
    )


KAFKA_DEFAULTS: dict[str, Any] = {"bootstrap_servers": "localhost:9092"}


@pytest.fixture(scope="session", name="kafka_config")
def fixture_kafka_config(env_config: dict[str, Any]) -> dict[str, Any]:
    return _service_config_from_env(env_config, "KAFKA", KAFKA_DEFAULTS)


MONGO_DEFAULTS: dict[str, Any] = {
    "hosts": "localhost",
    "port": 27017,
    "user": None,
    "password": None,
    "database": None,
    "auth_source": "admin",
}


@pytest.fixture(scope="session", name="mongo_config")
def fixture_mongo_config(env_config: dict[str, Any]) -> dict[str, Any]:
    return _service_config_from_env(env_config, "MONGO", MONGO_DEFAULTS, int_keys=frozenset({"port"}))


RABBITMQ_DEFAULTS: dict[str, Any] = {
    "host": "localhost",
    "port": 5672,
    "user": "guest",
    "password": "guest",
    "vhost": "/",
}


@pytest.fixture(scope="session", name="rabbitmq_config")
def fixture_rabbitmq_config(env_config: dict[str, Any]) -> dict[str, Any]:
    return _service_config_from_env(env_config, "RABBITMQ", RABBITMQ_DEFAULTS, int_keys=frozenset({"port"}))


OPENSEARCH_DEFAULTS: dict[str, Any] = {"hosts": ["localhost:9200"]}


@pytest.fixture(scope="session", name="opensearch_config")
def fixture_opensearch_config(env_config: dict[str, Any]) -> dict[str, Any]:
    result = dict(OPENSEARCH_DEFAULTS)
    val = env_config.get("OPENSEARCH_HOSTS")
    if val is not None:
        result["hosts"] = [v.strip() for v in str(val).split(",")]
    return result


POSTGRES_DEFAULTS: dict[str, Any] = {
    "host": "localhost",
    "port": 5432,
    "user": None,
    "password": None,
    "database": None,
}


@pytest.fixture(scope="session", name="base_postgresql_config")
def fixture_base_postgresql_config(env_config: dict[str, Any]) -> dict[str, Any]:
    return _service_config_from_env(env_config, "POSTGRES", POSTGRES_DEFAULTS, int_keys=frozenset({"port"}))
