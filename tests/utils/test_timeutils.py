#!/usr/bin/env python3


from pytbox.utils.timeutils import TimeUtils


def test_get_timestamp():
    assert isinstance(TimeUtils.get_timestamp(now=True), int)


if __name__ == "__main__":
    test_get_timestamp()