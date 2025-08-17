#!/usr/bin/env python3


import time
from pytbox.utils.timeutils import TimeUtils


def test_get_timestamp():
    assert TimeUtils.get_timestamp() == int(time.time())
    assert TimeUtils.get_timestamp(now=False) == int(time.time() * 1000)


if __name__ == "__main__":
    test_get_timestamp()