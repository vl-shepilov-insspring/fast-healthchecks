"""This module provides a health check for PostgreSQL using psycopg.

Classes:
    PostgreSQLPsycopgHealthCheck: A class for health checking PostgreSQL using psycopg.

Usage:
    The PostgreSQLPsycopgHealthCheck class can be used to perform health checks on a PostgreSQL database by
    connecting to the database and executing a simple query.

Example:
    health_check = PostgreSQLPsycopgHealthCheck(
        host="localhost",
        port=5432,
        user="username",
        password="password",
        database="dbname"
    )
    # or
    health_check = PostgreSQLPsycopgHealthCheck.from_dsn(
        "postgresql://username:password@localhost:5432/dbname",
    )
    result = await health_check()
    print(result.healthy)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fast_healthchecks.checks._base import DEFAULT_HC_TIMEOUT, healthcheck_safe
from fast_healthchecks.checks._imports import raise_optional_import_error
from fast_healthchecks.checks.dsn_parsing import PostgresParseDSNResult, SslMode
from fast_healthchecks.checks.postgresql.base import BasePostgreSQLHealthCheck
from fast_healthchecks.models import HealthCheckResult

try:
    import psycopg
except ImportError as exc:
    raise_optional_import_error("psycopg", "psycopg", exc)

if TYPE_CHECKING:
    from psycopg import AsyncConnection


class PostgreSQLPsycopgHealthCheck(BasePostgreSQLHealthCheck[HealthCheckResult]):
    """Health check class for PostgreSQL using psycopg.

    Attributes:
        _name: The name of the health check.
        _host: The hostname of the PostgreSQL server.
        _port: The port number of the PostgreSQL server.
        _user: The username for authentication.
        _password: The password for authentication.
        _database: The database name.
        _sslmode: The SSL mode to use for the connection.
        _sslcert: The path to the SSL certificate file.
        _sslkey: The path to the SSL key file.
        _sslrootcert: The path to the SSL root certificate file.
        _timeout: The timeout for the health check.
    """

    __slots__ = (
        "_database",
        "_host",
        "_name",
        "_password",
        "_port",
        "_sslcert",
        "_sslkey",
        "_sslmode",
        "_sslrootcert",
        "_timeout",
        "_user",
    )

    _host: str
    _port: int
    _user: str | None
    _password: str | None
    _database: str | None
    _sslmode: SslMode | None
    _sslcert: str | None
    _sslkey: str | None
    _sslrootcert: str | None
    _timeout: float
    _name: str

    def __init__(  # noqa: PLR0913
        self,
        *,
        host: str,
        port: int,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        sslmode: SslMode | None = None,
        sslcert: str | None = None,
        sslkey: str | None = None,
        sslrootcert: str | None = None,
        timeout: float = DEFAULT_HC_TIMEOUT,
        name: str = "PostgreSQL",
    ) -> None:
        """Initialize the PostgreSQLPsycopgHealthCheck.

        Args:
            host: The hostname of the PostgreSQL server.
            port: The port number of the PostgreSQL server.
            user: The username for authentication.
            password: The password for authentication.
            database: The database name.
            sslmode: The SSL mode to use for the connection.
            sslcert: The path to the SSL certificate file.
            sslkey: The path to the SSL key file.
            sslrootcert: The path to the SSL root certificate file.
            timeout: The timeout for the health check.
            name: The name of the health check.
        """
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database
        self._sslmode = sslmode
        self._sslcert = sslcert
        self._sslkey = sslkey
        self._sslrootcert = sslrootcert
        self._timeout = timeout
        self._name = name

    @classmethod
    def _from_parsed_dsn(
        cls,
        parsed: PostgresParseDSNResult,
        *,
        name: str = "PostgreSQL",
        timeout: float = DEFAULT_HC_TIMEOUT,
        **kwargs: Any,  # noqa: ARG003, ANN401
    ) -> PostgreSQLPsycopgHealthCheck:
        parse_result = parsed["parse_result"]
        return cls(
            host=parse_result.hostname or "localhost",
            port=parse_result.port or 5432,
            user=parse_result.username,
            password=parse_result.password,
            database=parse_result.path.lstrip("/"),
            sslmode=parsed["sslmode"],
            sslcert=parsed["sslcert"],
            sslkey=parsed["sslkey"],
            sslrootcert=parsed["sslrootcert"],
            timeout=timeout,
            name=name,
        )

    @healthcheck_safe(invalidate_on_error=False)
    async def __call__(self) -> HealthCheckResult:
        """Perform the health check.

        Returns:
            HealthCheckResult: The result of the health check.
        """
        connection: AsyncConnection | None = None
        try:
            connection = await psycopg.AsyncConnection.connect(
                host=self._host,
                port=self._port,
                user=self._user,
                password=self._password,
                dbname=self._database,
                sslmode=self._sslmode,
                sslcert=self._sslcert,
                sslkey=self._sslkey,
                sslrootcert=self._sslrootcert,
                connect_timeout=int(self._timeout),
            )
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT 1")
                healthy: bool = bool(await cursor.fetchone())
                return HealthCheckResult(name=self._name, healthy=healthy)
        finally:
            if connection is not None and not connection.closed:
                await connection.cancel_safe(timeout=self._timeout)
                await connection.close()

    def _build_dict(self) -> dict[str, Any]:
        return {
            "host": self._host,
            "port": self._port,
            "user": self._user,
            "password": self._password,
            "database": self._database,
            "sslmode": self._sslmode,
            "sslcert": self._sslcert,
            "sslkey": self._sslkey,
            "sslrootcert": self._sslrootcert,
            "timeout": self._timeout,
            "name": self._name,
        }
