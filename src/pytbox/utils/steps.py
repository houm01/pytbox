#!/usr/bin/env python3


import time


def run_step(log, name: str, fn, *args, **kwargs):
    """
    执行step。

    Args:
        log: log 参数。
        name: name 参数。
        fn: fn 参数。
        *args: 可变参数。
        **kwargs: 可变参数。

    Returns:
        Any: 返回值。
    """
    start = time.perf_counter()
    log.info(f"[{name}] -> {name}")

    try:
        result = fn(*args, **kwargs)
    except Exception:
        cost = time.perf_counter() - start
        log.exception(
            f"[{name}] !! {name} failed cost={cost:.3f}s, result={result}",
            
        )
        raise
    else:
        cost = time.perf_counter() - start
        log.info(
            f"[{name}] <- {name} ok cost={cost:.3f}s, result={result}",
            
        )
        return result
