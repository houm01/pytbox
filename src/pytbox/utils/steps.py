#!/usr/bin/env python3


import time


def run_step(log, name: str, fn, *args, **kwargs):
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
