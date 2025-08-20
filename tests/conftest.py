#!/usr/bin/env python3
"""
pytest 配置文件，定义测试用的 fixtures
"""

import pytest


@pytest.fixture
def target():
    """提供测试用的目标主机地址"""
    return "121.46.237.185"


@pytest.fixture(params=["121.46.237.185", "8.8.8.8", "114.114.114.114"])
def ping_targets(request):
    """提供多个测试目标，用于参数化测试"""
    return request.param

