<h1 align="center" style="vertical-align: middle;">
  <img src="https://raw.githubusercontent.com/shepilov-vladislav/fast-healthchecks/refs/heads/main/docs/img/green.svg" width="30"> <strong>Fast Healthchecks</strong>
</h1>

<b>Framework-agnostic health checks with integrations for the most popular ASGI frameworks: [FastAPI](https://github.com/fastapi/fastapi) / [FastStream](https://github.com/airtai/faststream) / [Litestar](https://github.com/litestar-org/litestar) to help you implement the [Health Check API](https://microservices.io/patterns/observability/health-check-api.html) pattern</b>

---

<p align="center">

  <a href="https://github.com/shepilov-vladislav/fast-healthchecks/actions/workflows/1_test.yml" target="_blank">
    <img src="https://github.com/shepilov-vladislav/fast-healthchecks/actions/workflows/1_test.yml/badge.svg?branch=main" alt="Test Passing"/>
  </a>

  <a href="https://codecov.io/gh/shepilov-vladislav/fast-healthchecks" target="_blank">
    <img src="https://codecov.io/gh/shepilov-vladislav/fast-healthchecks/branch/main/graph/badge.svg" alt="Coverage"/>
  </a>

  <a href="https://www.pepy.tech/projects/fast-healthchecks" target="_blank">
    <img src="https://static.pepy.tech/personalized-badge/fast-healthchecks?period=month&units=international_system&left_color=grey&right_color=green&left_text=downloads/month" alt="Downloads"/>
  </a>

  <a href="https://pypi.org/project/fast-healthchecks" target="_blank">
    <img src="https://img.shields.io/pypi/v/fast-healthchecks?label=PyPI" alt="Package version"/>
  </a>

  <a href="https://pypi.org/project/fast-healthchecks" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/fast-healthchecks.svg" alt="Supported Python versions"/>
  </a>

  <a href="https://github.com/shepilov-vladislav/fast-healthchecks/blob/main/LICENSE" target="_blank">
    <img src="https://img.shields.io/github/license/shepilov-vladislav/fast-healthchecks.png" alt="License"/>
  </a>

  <a href="https://shepilov-vladislav.github.io/fast-healthchecks/" target="_blank">
    <img src="https://img.shields.io/badge/docs-online-green" alt="Documentation"/>
  </a>

</p>

---

## Installation

`pip install fast-healthchecks` (or `poetry add` / `uv add`). Backends and framework integrations are optional extras. See [documentation → Installation](https://shepilov-vladislav.github.io/fast-healthchecks/installation/) for all options and extra names.

## Quick Start

Usage depends on the framework (FastAPI: `HealthcheckRouter`; FastStream / Litestar: `health()` from the corresponding integration). Full examples, configuration, lifecycle and shutdown, URL/SSRF, and DSN formats are in the [documentation](https://shepilov-vladislav.github.io/fast-healthchecks/). Example projects: [FastAPI](./examples/fastapi_example), [FastStream](./examples/faststream_example), [Litestar](./examples/litestar_example).

- **Configuration, shutdown, probe options:** [documentation](https://shepilov-vladislav.github.io/fast-healthchecks/).
- **Public API and `to_dict()`:** [API Reference](https://shepilov-vladislav.github.io/fast-healthchecks/api/).
- **PostgreSQL TLS certificate rotation:** [DSN formats](https://shepilov-vladislav.github.io/fast-healthchecks/dsn-formats/#postgresql-tls-certificate-rotation).

## Development

For the full list of recipes and their descriptions, run `just` or `just --list` (source of truth: justfile).

- **Changelog:** [CHANGELOG.md](CHANGELOG.md) in the repo; [Changelog](https://shepilov-vladislav.github.io/fast-healthchecks/changelog/) in the online docs.
- **Architecture decisions:** [Decisions (ADR)](https://shepilov-vladislav.github.io/fast-healthchecks/decisions/) in the online docs.
- **Security:** See [SECURITY.md](SECURITY.md) for how to report vulnerabilities.

### Setup environment

```bash
git clone https://github.com/shepilov-vladislav/fast-healthchecks.git
cd fast-healthchecks
uv sync --group=dev --group=docs --all-extras
```

### Run linters

```bash
just lint
```

### Running tests

- **Import tests:** `just tests-imports` — verifies ImportError messages when optional deps are missing; runs with minimal install (`uv sync --group=dev` only, no extras).
- **Unit tests:** `just tests-unit` — runs pytest with `-m unit`. Expects dev deps and optional extras already installed (e.g. after `uv sync --group=dev --all-extras` or after `just tests-integration`). FastStream unit tests use `TestKafkaBroker(connect_only=True)` and `TestApp` so no real Kafka is required.
- **Integration tests:** `just tests-integration` — requires Docker and `docker compose`; brings services up, runs integration tests, then brings them down. Set `DOCKER_SERVICES_UP=1` to skip compose up/down when services are already running.
- **Full suite:** `just tests-all` — runs import tests, then integration (compose up, pytest integration, compose down), then unit tests. Requires Docker.

Certificates in `tests/certs/` are for tests only; see CONTRIBUTING § Test certificates.

CI runs pre-commit, import tests, and unit tests on push/PR; integration tests run only on manual workflow dispatch or schedule.

### Serve documentation

```bash
just serve-docs
```

### Release and CI (maintainers)

Bump, rollback, workflows, secrets, pre-commit, and dependency updates: see [CONTRIBUTING § CI and release](CONTRIBUTING.md#ci-and-release) and the [workflows table](CONTRIBUTING.md#workflows) there. Quick links: [Bump version](https://github.com/shepilov-vladislav/fast-healthchecks/actions/workflows/2_bump.yml), [Rollback release](https://github.com/shepilov-vladislav/fast-healthchecks/actions/workflows/2_rollback.yml).

## Known alternatives

- [FastAPI Health](https://github.com/Kludex/fastapi-health)
- [FastAPI Health Monitor](https://github.com/adamkirchberger/fastapi-health-monitor)
- [fastapi_healthz](https://github.com/matteocacciola/fastapi_healthz)
- [fastapi_healthcheck](https://github.com/jtom38/fastapi_healthcheck)

## License

This project is licensed under the terms of the MIT license.
