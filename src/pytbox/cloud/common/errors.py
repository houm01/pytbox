class PytboxError(Exception):
    """Base error for pytbox cloud modules."""


class InvalidRequest(PytboxError):
    """Bad input or missing params."""


class AuthError(PytboxError):
    """AK/SK invalid, signature invalid, token expired."""


class PermissionError(PytboxError):
    """No permission (IAM/RAM)."""


class ThrottledError(PytboxError):
    """Request throttled by upstream."""


class TimeoutError(PytboxError):
    """Network/SDK timeout."""


class NotFoundError(PytboxError):
    """Resource not found."""


class RegionError(PytboxError):
    """Invalid or unavailable region."""


class UpstreamError(PytboxError):
    """Upstream API error (5xx/unknown)."""

    def __init__(self, message: str, *, upstream_code: str | None = None):
        super().__init__(message)
        self.upstream_code = upstream_code
