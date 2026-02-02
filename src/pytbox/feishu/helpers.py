#!/usr/bin/env python3

from typing import Dict, Any


def pick(base: Dict[Any, Any], *keys: str) -> Dict[Any, Any]:
    """
    执行 pick 相关逻辑。

    Args:
        base: base 参数。
        *keys: 可变参数。

    Returns:
        Any: 返回值。
    """
    return {key: base[key] for key in keys if key in base and base[key] is not None}
