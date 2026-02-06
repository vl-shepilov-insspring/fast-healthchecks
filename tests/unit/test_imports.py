"""Tests for optional-check import errors and install hints."""

import importlib

import pytest

pytestmark = pytest.mark.imports


@pytest.mark.parametrize(
    ("module_path", "message_substring"),
    [
        (
            "fast_healthchecks.checks.postgresql.asyncpg",
            r"asyncpg is not installed. Install it with `pip install fast-healthchecks\[asyncpg\]`.",
        ),
        (
            "fast_healthchecks.checks.postgresql.psycopg",
            r"psycopg is not installed. Install it with `pip install fast-healthchecks\[psycopg\]`.",
        ),
        (
            "fast_healthchecks.checks.kafka",
            r"aiokafka is not installed. Install it with `pip install fast-healthchecks\[aiokafka\]`.",
        ),
        (
            "fast_healthchecks.checks.mongo",
            r"motor is not installed. Install it with `pip install fast-healthchecks\[motor\]`.",
        ),
        (
            "fast_healthchecks.checks.opensearch",
            r"opensearch-py is not installed. Install it with `pip install fast-healthchecks\[opensearch\]`.",
        ),
        (
            "fast_healthchecks.checks.rabbitmq",
            r"aio-pika is not installed. Install it with `pip install fast-healthchecks\[aio-pika\]`.",
        ),
        (
            "fast_healthchecks.checks.redis",
            r"redis is not installed. Install it with `pip install fast-healthchecks\[redis\]`.",
        ),
        (
            "fast_healthchecks.checks.url",
            r"httpx is not installed. Install it with `pip install fast-healthchecks\[httpx\]`.",
        ),
    ],
)
def test_import_error_optional_check(module_path: str, message_substring: str) -> None:
    """Importing optional check without extra raises ImportError with install hint."""
    with pytest.raises(ImportError, match=message_substring):
        importlib.import_module(module_path)
