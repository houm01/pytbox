"""Tests for pytbox.cloud.common.rest_contracts."""

from __future__ import annotations

import re

import pytest

from pytbox.cloud.common.rest_contracts import build_stats, iso8601_now, paginate_items


def test_iso8601_now_returns_utc_z() -> None:
    """iso8601_now should return UTC timestamp with trailing Z."""

    value = iso8601_now()
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", value)


def test_paginate_items_basic() -> None:
    """paginate_items should return deterministic page metadata."""

    result = paginate_items(["a", "b", "c", "d", "e"], page=2, page_size=2)
    assert result.items == ["c", "d"]
    assert result.page == 2
    assert result.page_size == 2
    assert result.total == 5
    assert result.total_pages == 3


def test_paginate_items_out_of_range_page_returns_empty_items() -> None:
    """paginate_items should keep metadata and return empty page when out of range."""

    result = paginate_items([1, 2], page=9, page_size=10)
    assert result.items == []
    assert result.total == 2
    assert result.total_pages == 1


def test_paginate_items_rejects_invalid_args() -> None:
    """paginate_items should reject page/page_size lower than 1."""

    with pytest.raises(ValueError):
        paginate_items([1], page=0, page_size=1)
    with pytest.raises(ValueError):
        paginate_items([1], page=1, page_size=0)


def test_build_stats_counts_status_and_region() -> None:
    """build_stats should aggregate by status and region with total."""

    items = [
        {"status": "running", "region": "cn-hangzhou"},
        {"status": "running", "region": "cn-hangzhou"},
        {"status": "stopped", "region": "cn-beijing"},
        {"status": "", "region": ""},
    ]
    stats = build_stats(items)
    assert stats["total"] == 4
    assert stats["by_status"] == {"running": 2, "stopped": 1}
    assert stats["by_region"] == {"cn-hangzhou": 2, "cn-beijing": 1}
