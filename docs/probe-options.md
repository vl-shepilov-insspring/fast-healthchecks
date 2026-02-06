# Probe options

| Parameter | Description |
|-----------|-------------|
| `name` | Probe identifier (e.g. `"liveness"`, `"readiness"`, `"startup"`). |
| `checks` | List of health checks to run. |
| `summary` | Custom description for the probe (used in responses). If omitted, a default is generated from `name`. |
| `allow_partial_failure` | If `True`, probe is healthy when at least one check passes. Default: `False`. |

To customize HTTP responses, pass `options=build_probe_route_options(...)` to `HealthcheckRouter` or `health()`. Build options with:

| Parameter | Description |
|-----------|-------------|
| `success_handler` | Handler for healthy responses. Receives `ProbeAsgiResponse`, returns response body (or `None` for empty). |
| `failure_handler` | Handler for unhealthy responses. Same signature as `success_handler`. |
| `success_status` | HTTP status for healthy (default: `204` No Content). |
| `failure_status` | HTTP status for unhealthy (default: `503`). |
| `debug` | Include check details in responses (default: `False`). |
| `prefix` | URL prefix for probe routes (default: `"/health"`). |
| `timeout` | Max seconds for all checks; on exceed returns failure (default: `None` = no limit). |

Example: `HealthcheckRouter(Probe(...), options=build_probe_route_options(debug=True, prefix="/health"))`.
