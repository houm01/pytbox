#!/usr/bin/env python3

import os
from pytbox.logger import AppLogger


log = AppLogger('test_logger', enable_victorialog=True, victorialog_url=os.getenv("VICTORIALOG_URL"))


def test_logger_info():
    log.info('test_logger_info')


if __name__ == "__main__":
    test_logger_info()