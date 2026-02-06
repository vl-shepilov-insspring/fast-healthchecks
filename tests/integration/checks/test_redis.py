from typing import Any

import pytest

from fast_healthchecks.checks.redis import RedisHealthCheck
from fast_healthchecks.models import HealthCheckResult
from tests.integration.test_assertions import (
    CONNECTION_REFUSED_FRAGMENTS,
    DNS_ERROR_FRAGMENTS,
    assert_error_contains_any,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_redis_check_success(redis_config: dict[str, Any]) -> None:
    check = RedisHealthCheck(
        host=redis_config["host"],
        port=redis_config["port"],
        user=redis_config["user"],
        password=redis_config["password"],
        database=redis_config["database"],
    )
    try:
        result = await check()
        assert result == HealthCheckResult(name="Redis", healthy=True, error_details=None)
    finally:
        await check.aclose()


@pytest.mark.asyncio
async def test_redis_check_failure(redis_config: dict[str, Any]) -> None:
    check = RedisHealthCheck(
        host="localhost2",
        port=redis_config["port"],
        user=redis_config["user"],
        password=redis_config["password"],
        database=redis_config["database"],
    )
    try:
        result = await check()
        assert result.healthy is False
        assert_error_contains_any(result.error_details, DNS_ERROR_FRAGMENTS)
    finally:
        await check.aclose()


@pytest.mark.asyncio
async def test_redis_check_connection_error(redis_config: dict[str, Any]) -> None:
    check = RedisHealthCheck(
        host=redis_config["host"],
        port=6380,
        user=redis_config["user"],
        password=redis_config["password"],
        database=redis_config["database"],
    )
    try:
        result = await check()
        assert result.healthy is False
        assert_error_contains_any(result.error_details, CONNECTION_REFUSED_FRAGMENTS)
    finally:
        await check.aclose()
