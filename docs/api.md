# API Reference

The root package `__all__` is the single source for stable root-level exports. Prefer ``from fast_healthchecks import Probe, run_probe, healthcheck_shutdown, HealthCheckReport, HealthCheckResult, Check, FunctionConfig`` and the exception hierarchy (``HealthCheckError``, ``HealthCheckTimeoutError``, ``HealthCheckSSRFError``). Check classes (e.g. ``RedisHealthCheck``) and other configs are available from ``fast_healthchecks.checks`` or their submodules (e.g. ``fast_healthchecks.checks.redis``). See `fast_healthchecks.__all__` and `fast_healthchecks.checks.__all__`.

Config types (e.g. `RedisConfig`, `UrlConfig`) in `fast_healthchecks.checks.configs` are part of the supported API for passing `config=...` to check constructors. The `to_dict()` methods on check classes are for internal test use only and are not part of the supported public API; do not rely on them in production code.

**Secrets and redaction:** Check and config `to_dict(redact_secrets=True)` redacts credential-style keys (same set as in `fast_healthchecks.utils`). The structured logging layer used by `run_probe` does not log config or secrets; see `fast_healthchecks.logging` and the run_probe docs.

## Exception hierarchy (public)

The following exceptions are part of the public API and are documented for callers who want to handle them explicitly. Existing code that catches `asyncio.TimeoutError` or `ValueError` continues to work, because the new types subclass those.

- **HealthCheckError** — Base for health-check-related exceptions.
- **HealthCheckTimeoutError** — Raised when a probe or check run times out. Subclass of `HealthCheckError` and `asyncio.TimeoutError`.
- **HealthCheckSSRFError** — Raised when URL/host SSRF validation fails (e.g. `validate_url_ssrf`, `validate_host_ssrf_async`). Subclass of `HealthCheckError` and `ValueError`. See [SSRF documentation](ssrf.md) for behaviour and edge cases.

::: fast_healthchecks.models
    options:
        heading_level: 3
        show_root_heading: false

::: fast_healthchecks.dsn
    options:
        heading_level: 3
        show_root_heading: false

## Checks

::: fast_healthchecks.checks.configs
    options:
        heading_level: 3
        show_root_heading: false

::: fast_healthchecks.checks.types

::: fast_healthchecks.checks.function

::: fast_healthchecks.checks.redis

::: fast_healthchecks.checks.kafka

::: fast_healthchecks.checks.mongo

::: fast_healthchecks.checks.opensearch

::: fast_healthchecks.checks.rabbitmq

::: fast_healthchecks.checks.url

::: fast_healthchecks.checks.postgresql.asyncpg

::: fast_healthchecks.checks.postgresql.psycopg

## Integrations

::: fast_healthchecks.integrations.base

::: fast_healthchecks.integrations.fastapi

::: fast_healthchecks.integrations.faststream

::: fast_healthchecks.integrations.litestar

::: fast_healthchecks.utils
