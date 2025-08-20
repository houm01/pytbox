#!/usr/bin/env python3

from pytbox.base import get_logger



log = get_logger('tests.test_logger')

def test_logger_info():
    log.info('test_logger_info')
    log.error('test error log2')


if __name__ == "__main__":
    test_logger_info()