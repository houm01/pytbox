#!/usr/bin/env python3

from typing import Dict, Any


def pick(base: Dict[Any, Any], *keys: str) -> Dict[Any, Any]:
    return {key: base[key] for key in keys if key in base and base[key] is not None}