#!/usr/bin/env python3


import time
from typing import Any, Callable, TypeVar


_T = TypeVar("_T")


def run_step(log: Any, name: str, fn: Callable[..., _T], *args: Any, **kwargs: Any) -> _T:
    """Execute one step and log execution details.

    Args:
        log: Logger-like object that provides ``info`` and ``exception``.
        name: Step name used in log messages.
        fn: Callable to run.
        *args: Positional arguments passed to ``fn``.
        **kwargs: Keyword arguments passed to ``fn``.

    Returns:
        _T: Return value from ``fn``.

    Raises:
        Exception: Re-raises any exception raised by ``fn``.
    """
    start = time.perf_counter()
    log.info(f"[{name}] -> {name}")

    try:
        result = fn(*args, **kwargs)
    except Exception:
        cost = time.perf_counter() - start
        log.exception(f"[{name}] !! {name} failed cost={cost:.3f}s")
        raise

    cost = time.perf_counter() - start
    log.info(f"[{name}] <- {name} ok cost={cost:.3f}s, result={result}")
    return result
