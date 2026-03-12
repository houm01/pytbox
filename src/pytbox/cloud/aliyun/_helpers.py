"""Shared helpers for Aliyun read-only resource wrappers."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ...schemas.response import ReturnResponse


def body_to_map(response: Any) -> dict[str, Any]:
    """Convert SDK response body to a plain dictionary.

    Args:
        response: SDK response object.

    Returns:
        dict[str, Any]: Parsed response body.
    """
    body = getattr(response, "body", None)
    if body is None:
        return {}
    to_map = getattr(body, "to_map", None)
    if callable(to_map):
        result = to_map()
        return result if isinstance(result, dict) else {}
    return {}


def extract_collection(
    body_map: dict[str, Any],
    *,
    container_key: str,
    item_key: str,
) -> list[dict[str, Any]]:
    """Extract a list of dictionary items from a nested SDK response.

    Args:
        body_map: Response body map.
        container_key: Top-level container key.
        item_key: Nested list key.

    Returns:
        list[dict[str, Any]]: Extracted item list.
    """
    container = body_map.get(container_key) or {}
    if not isinstance(container, dict):
        return []
    items = container.get(item_key) or []
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def extract_total(body_map: dict[str, Any], *keys: str) -> int | None:
    """Extract total-count like fields from a response.

    Args:
        body_map: Response body map.
        *keys: Candidate total keys.

    Returns:
        int | None: Parsed total when available.
    """
    for key in keys:
        raw_value = body_map.get(key)
        if isinstance(raw_value, int):
            return raw_value
        if isinstance(raw_value, str) and raw_value.isdigit():
            return int(raw_value)
    return None


def failure_response(error: Exception) -> ReturnResponse:
    """Build a unified failure response for external SDK calls.

    Args:
        error: Caught exception.

    Returns:
        ReturnResponse: Failure payload.
    """
    return ReturnResponse(code=1, msg="failed", data={"error": str(error)})


def serialize_sdk_value(value: Any) -> Any:
    """Serialize SDK model values into JSON-compatible Python data.

    Args:
        value: Arbitrary SDK result or nested attribute.

    Returns:
        Any: Serialized value.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {key: serialize_sdk_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [serialize_sdk_value(item) for item in value]

    for method_name in ("to_map", "to_dict"):
        method = getattr(value, method_name, None)
        if callable(method):
            try:
                return serialize_sdk_value(method())
            except Exception:  # noqa: BLE001
                pass

    attrs = getattr(value, "__dict__", None)
    if isinstance(attrs, dict) and attrs:
        return {
            key: serialize_sdk_value(item)
            for key, item in attrs.items()
            if not key.startswith("_") and not callable(item)
        }

    return str(value)
