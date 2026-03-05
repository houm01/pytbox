"""Common contracts and helpers for collector-style cloud REST data.

This module intentionally keeps a lightweight runtime surface:
- No external IO
- No framework-specific dependency
- TypedDict/dataclass contracts plus pure helper functions
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import ceil
from typing import Any, Generic, Iterable, Mapping, Sequence, TypeVar, TypedDict


T = TypeVar("T")


class InstanceContract(TypedDict, total=False):
    """Minimal instance contract shared by ECS/RDS/Redis."""

    id: str
    name: str
    status: str
    region: str
    created_at: str
    expired_at: str | None
    tags: dict[str, str]


class OrphanDiskContract(TypedDict, total=False):
    """Minimal orphan disk contract."""

    disk_id: str
    size_gb: int
    region: str
    created_at: str
    last_attached_at: str | None


class OrphanEipContract(TypedDict, total=False):
    """Minimal orphan EIP contract."""

    eip: str
    region: str
    bandwidth: int | None
    created_at: str


class StatsContract(TypedDict, total=False):
    """Common stats contract."""

    total: int
    by_status: dict[str, int]
    by_region: dict[str, int]


class StoragePointContract(TypedDict):
    """Timeseries point for storage metrics."""

    ts: str
    used_gb: float
    total_gb: float
    usage_pct: float


class AlertsStatsContract(TypedDict, total=False):
    """Security center alerts stats contract."""

    total: int
    by_severity: dict[str, int]
    by_type: dict[str, int]


class AccessKeyAuditContract(TypedDict, total=False):
    """Identity access key audit contract."""

    id: str
    created_at: str
    last_used_at: str | None


class UserAuditContract(TypedDict, total=False):
    """Identity user audit contract."""

    user_id: str
    user_name: str
    last_login_at: str | None
    mfa_enabled: bool
    access_keys: list[AccessKeyAuditContract]


@dataclass(frozen=True)
class PageResult(Generic[T]):
    """Pagination result for deterministic page-based list APIs.

    Attributes:
        items: Current page items.
        page: 1-based current page.
        page_size: Page size used.
        total: Total item count before slicing.
        total_pages: Total pages (0 if total == 0).
    """

    items: list[T]
    page: int
    page_size: int
    total: int
    total_pages: int


def iso8601_now() -> str:
    """Return current UTC time in ISO8601 with trailing 'Z'."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def paginate_items(items: Sequence[T], page: int, page_size: int) -> PageResult[T]:
    """Paginate a sequence deterministically.

    Args:
        items: Source sequence.
        page: 1-based page number.
        page_size: Positive page size.

    Returns:
        A PageResult carrying sliced items and page metadata.

    Raises:
        ValueError: If page < 1 or page_size < 1.
    """

    if page < 1:
        raise ValueError("page must be >= 1")
    if page_size < 1:
        raise ValueError("page_size must be >= 1")

    total = len(items)
    total_pages = ceil(total / page_size) if total else 0
    start = (page - 1) * page_size
    end = start + page_size
    page_items = list(items[start:end]) if start < total else []
    return PageResult(items=page_items, page=page, page_size=page_size, total=total, total_pages=total_pages)


def count_by(values: Iterable[str | None]) -> dict[str, int]:
    """Count string values.

    Empty strings or None values are skipped.
    """

    output: dict[str, int] = {}
    for raw in values:
        key = (raw or "").strip()
        if not key:
            continue
        output[key] = output.get(key, 0) + 1
    return output


def build_stats(
    items: Sequence[Mapping[str, Any]],
    *,
    status_key: str = "status",
    region_key: str = "region",
) -> StatsContract:
    """Build standard stats structure from mapping-like items.

    Args:
        items: Resource items.
        status_key: Item key for status.
        region_key: Item key for region.

    Returns:
        Stats contract with total/by_status/by_region.
    """

    by_status = count_by(str(item.get(status_key, "")).strip() for item in items)
    by_region = count_by(str(item.get(region_key, "")).strip() for item in items)
    return StatsContract(total=len(items), by_status=by_status, by_region=by_region)


__all__ = [
    "AccessKeyAuditContract",
    "AlertsStatsContract",
    "InstanceContract",
    "OrphanDiskContract",
    "OrphanEipContract",
    "PageResult",
    "StatsContract",
    "StoragePointContract",
    "UserAuditContract",
    "build_stats",
    "count_by",
    "iso8601_now",
    "paginate_items",
]
