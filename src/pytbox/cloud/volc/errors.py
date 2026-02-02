class PytboxError(Exception):
    """
    PytboxError 类。

    用于 Pytbox Error 相关能力的封装。
    """
    pass


class AuthError(PytboxError):
    """
    AuthError 类。

    用于 Auth Error 相关能力的封装。
    """
    pass


class PermissionError(PytboxError):
    """
    PermissionError 类。

    用于 Permission Error 相关能力的封装。
    """
    pass


class ThrottledError(PytboxError):
    """
    ThrottledError 类。

    用于 Throttled Error 相关能力的封装。
    """
    pass


class TimeoutError(PytboxError):
    """
    TimeoutError 类。

    用于 Timeout Error 相关能力的封装。
    """
    pass


class UpstreamError(PytboxError):
    """
    UpstreamError 类。

    用于 Upstream Error 相关能力的封装。
    """
    pass

class InvalidRequest(PytboxError):
    """
    InvalidRequest 类。

    用于 Invalid Request 相关能力的封装。
    """
    pass


def map_volc_exception(action: str, e: Exception) -> Exception:
    """
    映射volc exception。

    Args:
        action: action 参数。
        e: e 参数。

    Returns:
        Any: 返回值。
    """
    s = str(e).lower()

    # SDK 的 ApiException 通常带 body（json）
    body = getattr(e, "body", None)
    if body:
        try:
            j = json.loads(body)
            err = (((j.get("ResponseMetadata") or {}).get("Error")) or {})
            code = (err.get("Code") or "").strip()
            msg = (err.get("Message") or "").strip()

            cl = code.lower()
            ml = msg.lower()

            if cl in {"paramsvalueerror", "missingparameter", "invalidparameter"} or "param" in ml:
                return InvalidRequest(f"{action} invalid params: {code}")
            if cl in {"unauthorized", "invalidaccesskey", "signaturedoesnotmatch"}:
                return AuthError(f"{action} auth failed")
            if cl in {"forbidden", "accessdenied"}:
                return PermissionError(f"{action} permission denied")
            if "thrott" in cl or "ratelimit" in ml:
                return ThrottledError(f"{action} throttled")
        except Exception:
            pass

    if "timeout" in s or "timed out" in s:
        return TimeoutError(f"{action} timeout")
    if "forbidden" in s or "access denied" in s:
        return PermissionError(f"{action} permission denied")
    if "thrott" in s or "too many requests" in s:
        return ThrottledError(f"{action} throttled")

    return UpstreamError(f"{action} upstream error")
