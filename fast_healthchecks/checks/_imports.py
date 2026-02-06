"""Helpers for optional dependency imports."""

from __future__ import annotations

from typing import NoReturn


def raise_optional_import_error(extra: str, package: str, exc: ImportError) -> NoReturn:
    """Raise ImportError with install hint. Call from except ImportError handler.

    Raises:
        ImportError: Always, with message directing user to install the extra.
    """
    msg = f"{package} is not installed. Install it with `pip install fast-healthchecks[{extra}]`."
    raise ImportError(msg) from exc
