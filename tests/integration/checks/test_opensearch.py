from typing import Any

import pytest

from fast_healthchecks.checks.opensearch import OpenSearchHealthCheck
from fast_healthchecks.models import HealthCheckResult
from tests.integration.test_assertions import (
    CONNECTION_REFUSED_FRAGMENTS,
    DNS_ERROR_FRAGMENTS,
    assert_error_contains_any,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_opensearch_check_success(opensearch_config: dict[str, Any]) -> None:
    check = OpenSearchHealthCheck(**opensearch_config)
    result = await check()
    assert result == HealthCheckResult(name="OpenSearch", healthy=True, error_details=None)


@pytest.mark.asyncio
async def test_opensearch_check_failure(opensearch_config: dict[str, Any]) -> None:
    config: dict[str, Any] = {
        **opensearch_config,
        "hosts": ["localhost2:9200"],
    }
    check = OpenSearchHealthCheck(**config)
    result = await check()
    assert result.healthy is False
    assert_error_contains_any(result.error_details, DNS_ERROR_FRAGMENTS)


@pytest.mark.asyncio
async def test_opensearch_check_connection_error(opensearch_config: dict[str, Any]) -> None:
    config: dict[str, Any] = {
        **opensearch_config,
        "hosts": ["localhost:9300"],
    }
    check = OpenSearchHealthCheck(**config)
    result = await check()
    assert result.healthy is False
    assert_error_contains_any(result.error_details, CONNECTION_REFUSED_FRAGMENTS)
