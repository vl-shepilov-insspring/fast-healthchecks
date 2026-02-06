from typing import Any

import pytest

from fast_healthchecks.checks.kafka import KafkaHealthCheck
from fast_healthchecks.models import HealthCheckResult

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_kafka_check_success(kafka_config: dict[str, Any]) -> None:
    check = KafkaHealthCheck(**kafka_config)
    result = await check()
    assert result == HealthCheckResult(name="Kafka", healthy=True, error_details=None)


@pytest.mark.asyncio
async def test_kafka_check_failure(kafka_config: dict[str, Any]) -> None:
    config: dict[str, Any] = {
        **kafka_config,
        "bootstrap_servers": "localhost2:9093",
    }
    check = KafkaHealthCheck(**config)
    result = await check()
    assert result.healthy is False
    assert result.error_details is not None
    assert "Unable to bootstrap from" in result.error_details


@pytest.mark.asyncio
async def test_kafka_check_connection_error(kafka_config: dict[str, Any]) -> None:
    # Use closed port to guarantee connection refused (not a running broker)
    config: dict[str, Any] = {
        **kafka_config,
        "bootstrap_servers": "localhost:19092",
    }
    check = KafkaHealthCheck(**config)
    result = await check()
    assert result.healthy is False
    assert result.error_details is not None
    assert "Unable to bootstrap from" in result.error_details
