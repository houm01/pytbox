#!/usr/bin/env python3

import logging
import re

from pytbox.utils.timeutils import TimeUtils


def test_get_timestamp() -> None:
    """`get_timestamp` should return int."""
    assert isinstance(TimeUtils.get_timestamp(now=True), int)


def test_get_timestamp_last_day_respects_unit(monkeypatch) -> None:
    """`get_timestamp_last_day` should honor both ms and s units."""
    fixed_now_s = 1_700_000_000
    monkeypatch.setattr("pytbox.utils.timeutils.time.time", lambda: fixed_now_s)

    assert TimeUtils.get_timestamp_last_day(last_days=0, unit="ms") == fixed_now_s * 1000
    assert TimeUtils.get_timestamp_last_day(last_days=0, unit="s") == fixed_now_s
    assert TimeUtils.get_timestamp_last_day(last_days=1, unit="ms") == fixed_now_s * 1000 - 86_400 * 1000
    assert TimeUtils.get_timestamp_last_day(last_days=1, unit="s") == fixed_now_s - 86_400


def test_get_last_month_start_and_end_time_returns_strings() -> None:
    """`get_last_month_start_and_end_time` should return formatted strings."""
    start_time, end_time = TimeUtils.get_last_month_start_and_end_time()
    pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"

    assert isinstance(start_time, str)
    assert isinstance(end_time, str)
    assert re.match(pattern, start_time)
    assert re.match(pattern, end_time)


def test_convert_syslog_huawei_str_to_8601_invalid_logs_warning(caplog) -> None:
    """Invalid input should return None and emit warning log."""
    caplog.set_level(logging.WARNING, logger="pytbox.utils.timeutils")
    result = TimeUtils.convert_syslog_huawei_str_to_8601("invalid-time")

    assert result is None
    assert any("时间转换失败" in record.message for record in caplog.records)
