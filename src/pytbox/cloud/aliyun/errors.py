from Tea.exceptions import TeaException, UnretryableException


class PytboxError(Exception):
    """Base error for pytbox."""


class AuthError(PytboxError):
    pass


class PermissionError(PytboxError):
    pass


class ThrottledError(PytboxError):
    pass


class TimeoutError(PytboxError):
    pass


class NotFoundError(PytboxError):
    pass


class RegionError(PytboxError):
    pass


class UpstreamError(PytboxError):
    def __init__(self, message: str, *, upstream_code: str | None = None):
        super().__init__(message)
        self.upstream_code = upstream_code


def map_tea_exception(action: str, e: Exception) -> Exception:
    # 不可重试上游异常
    if isinstance(e, UnretryableException):
        return UpstreamError(f"{action} upstream unretryable error")

    # 非 TeaException：先做字符串兜底
    if not isinstance(e, TeaException):
        s = str(e).lower()
        if "timeout" in s or "timed out" in s:
            return TimeoutError(f"{action} timeout")
        return UpstreamError(f"{action} upstream error")

    code = (getattr(e, "code", None) or "").strip()
    msg = (getattr(e, "message", None) or str(e) or "").strip()
    cl = code.lower()
    ml = msg.lower()

    # 鉴权
    if cl in {"invalidaccesskeyid", "signaturedoesnotmatch"} or \
       "invalidaccesskeyid" in ml or "signaturedoesnotmatch" in ml:
        return AuthError(f"{action} auth failed")

    # 权限
    if cl in {"forbidden", "accessdenied", "unauthorizedoperation"} or \
       "forbidden" in ml or "access denied" in ml or "not authorized" in ml:
        return PermissionError(f"{action} permission denied")

    # 限流
    if "throttl" in cl or cl in {"toomanyrequests"} or \
       "throttl" in ml or "too many requests" in ml:
        return ThrottledError(f"{action} throttled")

    # region / not found
    if cl in {"invalidregionid"} or "invalidregionid" in ml:
        return RegionError(f"{action} invalid region")
    if "notfound" in cl or "not found" in ml:
        return NotFoundError(f"{action} not found")

    # 超时
    if "timeout" in ml or "timed out" in ml:
        return TimeoutError(f"{action} timeout")

    return UpstreamError(f"{action} upstream error", upstream_code=code or None)
