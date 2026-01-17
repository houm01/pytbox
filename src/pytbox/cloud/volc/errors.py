class PytboxError(Exception):
    pass


class AuthError(PytboxError):
    pass


class PermissionError(PytboxError):
    pass


class ThrottledError(PytboxError):
    pass


class TimeoutError(PytboxError):
    pass


class UpstreamError(PytboxError):
    pass

class InvalidRequest(PytboxError):
    pass


def map_volc_exception(action: str, e: Exception) -> Exception:
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