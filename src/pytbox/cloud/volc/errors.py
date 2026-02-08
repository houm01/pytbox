"""Volc cloud error mapping."""

from __future__ import annotations

import json


class PytboxError(Exception):
    """Base cloud error."""


class AuthError(PytboxError):
    """Authentication failure."""


class PermissionError(PytboxError):
    """Permission denied."""


class ThrottledError(PytboxError):
    """Request throttled by upstream."""


class TimeoutError(PytboxError):
    """Request timeout."""


class UpstreamError(PytboxError):
    """Unknown upstream error."""


class InvalidRequest(PytboxError):
    """Bad request from client input."""


def map_volc_exception(action: str, e: Exception) -> Exception:
    """Map Volc SDK errors to pytbox cloud errors.

    Args:
        action: Action name for contextual message.
        e: Original raised exception.

    Returns:
        Exception: Mapped cloud exception.
    """
    raw_message = str(e).lower()
    body = getattr(e, "body", None)
    if body:
        try:
            body_json = json.loads(body)
            error = (body_json.get("ResponseMetadata", {}).get("Error")) or {}
            code = str(error.get("Code") or "").strip()
            message = str(error.get("Message") or "").strip()
            code_lower = code.lower()
            message_lower = message.lower()

            if code_lower in {"paramsvalueerror", "missingparameter", "invalidparameter"} or "param" in message_lower:
                return InvalidRequest(f"{action} invalid params: {code}")
            if code_lower in {"unauthorized", "invalidaccesskey", "signaturedoesnotmatch"}:
                return AuthError(f"{action} auth failed")
            if code_lower in {"forbidden", "accessdenied"}:
                return PermissionError(f"{action} permission denied")
            if "thrott" in code_lower or "ratelimit" in message_lower:
                return ThrottledError(f"{action} throttled")
        except Exception:  # noqa: BLE001
            pass

    if "timeout" in raw_message or "timed out" in raw_message:
        return TimeoutError(f"{action} timeout")
    if "forbidden" in raw_message or "access denied" in raw_message:
        return PermissionError(f"{action} permission denied")
    if "thrott" in raw_message or "too many requests" in raw_message:
        return ThrottledError(f"{action} throttled")
    return UpstreamError(f"{action} upstream error")
