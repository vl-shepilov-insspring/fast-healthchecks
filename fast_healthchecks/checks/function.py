"""This module provides a health check class for functions.

Classes:
    FunctionHealthCheck: A class to perform health checks on a function.

Usage:
    The FunctionHealthCheck class can be used to perform health checks on a function by calling it.

Example:
    def my_function():
        return True

    health_check = FunctionHealthCheck(func=my_function)
    result = await health_check()
    print(result.healthy)
"""

from __future__ import annotations

import asyncio
import functools
import inspect
from concurrent.futures import Executor
from typing import TYPE_CHECKING, Any, final

from fast_healthchecks.checks._base import DEFAULT_HC_TIMEOUT, HealthCheck, healthcheck_safe
from fast_healthchecks.models import HealthCheckResult

if TYPE_CHECKING:
    from collections.abc import Callable


@final
class FunctionHealthCheck(HealthCheck[HealthCheckResult]):
    """A class to perform health checks on a function.

    Synchronous functions are run via ``loop.run_in_executor(executor, ...)``.
    The default executor is ``None`` (shared thread pool). Long-running blocking
    sync checks can exhaust the pool; pass a dedicated :class:`Executor` if needed.

    Attributes:
        _args: The arguments to pass to the function.
        _executor: The executor for sync functions.
        _func: The function to perform the health check on.
        _kwargs: The keyword arguments to pass to the function.
        _name: The name of the health check.
        _timeout: The timeout for the health check.
    """

    __slots__ = ("_args", "_executor", "_func", "_kwargs", "_name", "_timeout")

    _func: Callable[..., Any]
    _args: tuple[Any, ...]
    _kwargs: dict[str, Any]
    _executor: Executor | None
    _timeout: float
    _name: str

    def __init__(  # noqa: PLR0913
        self,
        *,
        func: Callable[..., Any],
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        executor: Executor | None = None,
        timeout: float = DEFAULT_HC_TIMEOUT,
        name: str = "Function",
    ) -> None:
        """Initialize the FunctionHealthCheck.

        Args:
            func: The function to perform the health check on.
            args: The arguments to pass to the function.
            kwargs: The keyword arguments to pass to the function.
            executor: Executor for sync functions. Defaults to None (thread pool).
            timeout: The timeout for the health check.
            name: The name of the health check.
        """
        self._func = func
        self._args = args or ()
        self._kwargs = kwargs or {}
        self._executor = executor
        self._timeout = timeout
        self._name = name

    @healthcheck_safe(invalidate_on_error=False)
    async def __call__(self) -> HealthCheckResult:
        """Perform the health check on the function.

        Sync functions run in the given executor (default: shared thread pool).

        Returns:
            HealthCheckResult: The result of the health check.
        """
        task: asyncio.Future[Any]
        if inspect.iscoroutinefunction(self._func):
            task = self._func(*self._args, **self._kwargs)
        else:
            loop = asyncio.get_running_loop()
            task = loop.run_in_executor(
                self._executor,
                functools.partial(self._func, *self._args, **self._kwargs),
            )
        result = await asyncio.wait_for(task, timeout=self._timeout)
        healthy = bool(result) if isinstance(result, bool) else True
        return HealthCheckResult(name=self._name, healthy=healthy)
