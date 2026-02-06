# Lifecycle and shutdown

## Open client mechanics

Checks that cache a client (Redis, Mongo, Kafka, OpenSearch, URL, RabbitMQ, PostgreSQL) keep one connection per instance. Such checks implement ``aclose()`` and are said to hold an **open client**. Open clients are **not** closed inside `run_probe`; they are closed only by the **documented shutdown path** below.

- **Which checks have open clients:** Any check that has an `aclose` method (e.g. those using `ClientCachingMixin`). Function-based checks and checks without `aclose` do not hold open clients.
- **Which shutdown path closes them:** Only `healthcheck_shutdown(probes)` or `close_probes(probes)` (path **Y**). On cancellation or timeout of `run_probe`, cached clients are **not** closed; the caller is responsible for calling the shutdown path (path **X**) so that **Y** runs.

## Cleanup paths (X and Y)

- **X (when cleanup runs):** The caller invokes `healthcheck_shutdown(probes)` (or `close_probes(probes)`) after using the probes—typically in the framework’s lifespan/shutdown hook. On cancellation or timeout of `run_probe`, `run_probe` does **not** close cached clients; the caller should still call the shutdown path so that resources are closed.
- **Y (what closes open clients):** `close_probes(probes)` (and thus `healthcheck_shutdown(probes)`) calls `aclose()` on each check that has it. Cached clients are closed only by this path, not inside `run_probe`.

After cancel or timeout there are no dangling background tasks from `run_probe` (the probe’s check tasks are cancelled); a cached client may remain open until the caller invokes **Y**.

## Framework shutdown

To close health check resources on app shutdown:

- **FastAPI:** Store the router and call `await router.close()` in your [lifespan](https://fastapi.tiangolo.com/advanced/events/) context manager (after `yield`), or use `healthcheck_shutdown(probes)` and call the returned callback in lifespan.
- **FastStream:** Pass the callback from `healthcheck_shutdown(probes)` into your app's `on_shutdown` list, e.g. `AsgiFastStream(..., on_shutdown=[healthcheck_shutdown(probes)])`.
- **Litestar:** Pass the callback from `healthcheck_shutdown(probes)` into the app's `on_shutdown` list, e.g. `Litestar(..., on_shutdown=[healthcheck_shutdown(probes)])`.

Import `healthcheck_shutdown` from `fast_healthchecks.integrations.fastapi`, `fast_healthchecks.integrations.faststream`, or `fast_healthchecks.integrations.litestar`.
