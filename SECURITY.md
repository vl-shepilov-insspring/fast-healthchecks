# Security policy

## URL checks and SSRF

Health check URLs must come from trusted configuration only. Do not use user-controlled input. For URL/SSRF behaviour, allowed schemes, `block_private_hosts`, and edge cases, see the [SSRF documentation](docs/ssrf.md) in the docs.

## RabbitMQ default credentials

The RabbitMQ health check (and ``RabbitMQConfig``) default to ``user="guest"`` and ``password="guest"`` when not specified (e.g. when parsing a DSN without credentials). **Do not use these defaults in production or on any non-local broker.** They are intended for local development only. In production, set explicit credentials (e.g. from environment or a secrets manager) or use a DSN that includes the credentials.

## Reporting vulnerabilities

If you believe you have found a security vulnerability, please report it privately. Do not open a public issue.

**How to report:** Send details to the maintainer email in the project's `pyproject.toml`, or use [GitHub Security Advisories](https://github.com/shepilov-vladislav/fast-healthchecks/security/advisories/new) for this repository. Include steps to reproduce and impact if possible.

We will acknowledge receipt and work on a fix. Please do not disclose the issue publicly until a fix has been released or we have agreed on disclosure timing.
