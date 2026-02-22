"""Aliyun SLS resource operations."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Callable

from ...schemas.response import ReturnResponse

try:
    from aliyun.log import GetLogsRequest, LogItem, PutLogsRequest
    from aliyun.log import LogClient as SlsLogClient
    from aliyun.log.auth import AUTH_VERSION_4
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    GetLogsRequest = None  # type: ignore[assignment]
    LogItem = None  # type: ignore[assignment]
    PutLogsRequest = None  # type: ignore[assignment]
    SlsLogClient = None  # type: ignore[assignment]
    AUTH_VERSION_4 = None  # type: ignore[assignment]


class SLSResource:
    """Aliyun SLS read/write resource wrapper."""

    def __init__(self, client: Any, *, idempotency_ttl_seconds: int = 300) -> None:
        """Initialize SLS resource.

        Args:
            client: AliyunClient instance.
            idempotency_ttl_seconds: In-memory idempotency TTL for write operations.
        """
        self._c = client
        self._idempotency_ttl_seconds = max(idempotency_ttl_seconds, 1)
        self._idempotency_cache: dict[str, tuple[float, ReturnResponse]] = {}
        self._sls_client: Any | None = None

    def _sdk_unavailable_response(self) -> ReturnResponse:
        """Build failure response when SLS SDK is missing.

        Returns:
            ReturnResponse: Failure payload.
        """
        return ReturnResponse(code=1, msg="aliyun-log-python-sdk is required", data=None)

    @staticmethod
    def _failure_response(error: Exception) -> ReturnResponse:
        """Build unified failure response.

        Args:
            error: Caught exception.

        Returns:
            ReturnResponse: Failure payload.
        """
        return ReturnResponse(code=1, msg="failed", data={"error": str(error)})

    def _get_sls_client(self) -> Any | None:
        """Get or lazily create SLS SDK client.

        Returns:
            Any | None: SLS SDK client or ``None`` when SDK dependency is missing.
        """
        if SlsLogClient is None:
            return None
        if self._sls_client is None:
            endpoint = self._c.cfg.sls_endpoint or f"{self._c.cfg.region}.log.aliyuncs.com"
            self._sls_client = SlsLogClient(
                endpoint,
                self._c.creds.ak,
                self._c.creds.sk,
                auth_version=AUTH_VERSION_4,
                region=self._c.cfg.region,
            )
        return self._sls_client

    def get_logs(
        self,
        *,
        project: str,
        logstore: str,
        query: str,
        from_time: int,
        to_time: int,
    ) -> ReturnResponse:
        """Get logs from SLS.

        Args:
            project: SLS project name.
            logstore: SLS logstore name.
            query: Query expression.
            from_time: Query start unix timestamp.
            to_time: Query end unix timestamp.

        Returns:
            ReturnResponse: ``data`` is list of log item contents.
        """
        if GetLogsRequest is None:
            return self._sdk_unavailable_response()
        sls_client = self._get_sls_client()
        if sls_client is None:
            return self._sdk_unavailable_response()

        try:
            request = GetLogsRequest(project, logstore, from_time, to_time, query=query)
            response = self._c.call("sls_get_logs", lambda: sls_client.get_logs(request))
            logs = response.get_logs() if hasattr(response, "get_logs") else []
            result: list[Any] = []
            for log in logs:
                if hasattr(log, "contents"):
                    result.append(log.contents)
                else:
                    result.append(log)
            return ReturnResponse(code=0, msg="success", data=result)
        except Exception as error:  # noqa: BLE001
            return self._failure_response(error)

    def put_logs(
        self,
        *,
        project: str,
        logstore: str,
        topic: str = "program",
        level: str = "INFO",
        msg: str | None = None,
        app: str | None = None,
        caller_filename: str | None = None,
        caller_lineno: int | None = None,
        caller_function: str | None = None,
        call_full_filename: str | None = None,
    ) -> ReturnResponse:
        """Write program logs into SLS.

        Args:
            project: SLS project name.
            logstore: SLS logstore name.
            topic: SLS topic.
            level: Log level.
            msg: Log message.
            app: App name.
            caller_filename: Caller file name.
            caller_lineno: Caller line number.
            caller_function: Caller function name.
            call_full_filename: Caller absolute file path.

        Returns:
            ReturnResponse: Write result.
        """
        if LogItem is None or PutLogsRequest is None:
            return self._sdk_unavailable_response()
        sls_client = self._get_sls_client()
        if sls_client is None:
            return self._sdk_unavailable_response()

        normalized_level = level
        if level == "WARN":
            normalized_level = "WARNING"
        elif level == "EXCEPTION":
            normalized_level = "ERROR"

        def _safe_str(value: Any) -> str:
            """Convert optional value to SLS-safe string.

            Args:
                value: Any input value.

            Returns:
                str: Empty string when ``value`` is ``None``, otherwise stringified value.
            """
            return "" if value is None else str(value)

        contents = [
            ("level", _safe_str(normalized_level)),
            ("app", _safe_str(app)),
            ("msg", _safe_str(msg)),
            ("caller_filename", _safe_str(caller_filename)),
            ("caller_lineno", _safe_str(caller_lineno)),
            ("caller_function", _safe_str(caller_function)),
            ("call_full_filename", _safe_str(call_full_filename)),
        ]

        payload = {
            "project": project,
            "logstore": logstore,
            "topic": topic,
            "contents": contents,
        }
        key = self._build_idempotency_key("put_logs", payload)
        return self._run_idempotent(
            key=key,
            caller=lambda: self._put_logs_once(
                sls_client=sls_client,
                project=project,
                logstore=logstore,
                topic=topic,
                contents=contents,
            ),
        )

    def put_logs_for_meraki(
        self,
        *,
        project: str,
        logstore: str,
        alert: list[tuple[str, Any]],
    ) -> ReturnResponse:
        """Write Meraki alert logs into SLS.

        Args:
            project: SLS project name.
            logstore: SLS logstore name.
            alert: Key-value tuple list expected by SLS ``LogItem.set_contents``.

        Returns:
            ReturnResponse: Write result.
        """
        if LogItem is None or PutLogsRequest is None:
            return self._sdk_unavailable_response()
        sls_client = self._get_sls_client()
        if sls_client is None:
            return self._sdk_unavailable_response()

        payload = {
            "project": project,
            "logstore": logstore,
            "topic": "",
            "contents": alert,
        }
        key = self._build_idempotency_key("put_logs_for_meraki", payload)
        return self._run_idempotent(
            key=key,
            caller=lambda: self._put_logs_once(
                sls_client=sls_client,
                project=project,
                logstore=logstore,
                topic="",
                contents=alert,
            ),
        )

    def _put_logs_once(
        self,
        *,
        sls_client: Any,
        project: str,
        logstore: str,
        topic: str,
        contents: list[tuple[str, Any]],
    ) -> ReturnResponse:
        """Build and send one SLS PutLogs request.

        Args:
            sls_client: SLS SDK client.
            project: SLS project name.
            logstore: SLS logstore name.
            topic: SLS topic.
            contents: SLS log contents.

        Returns:
            ReturnResponse: Write result.
        """
        if LogItem is None or PutLogsRequest is None:
            return self._sdk_unavailable_response()

        try:
            log_item = LogItem()
            log_item.set_contents(contents)
            request = PutLogsRequest(
                project,
                logstore,
                topic,
                "",
                [log_item],
                compress=False,
            )
            self._c.call("sls_put_logs", lambda: sls_client.put_logs(request))
            return ReturnResponse(code=0, msg="success", data={"project": project, "logstore": logstore})
        except Exception as error:  # noqa: BLE001
            return self._failure_response(error)

    def _build_idempotency_key(self, operation: str, payload: dict[str, Any]) -> str:
        """Build idempotency key for write operations.

        Args:
            operation: Operation name.
            payload: Request payload.

        Returns:
            str: Idempotency key.
        """
        window = int(time.time() // self._idempotency_ttl_seconds)
        raw = f"{operation}|{window}|{json.dumps(payload, sort_keys=True, default=str)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _run_idempotent(self, *, key: str, caller: Callable[[], ReturnResponse]) -> ReturnResponse:
        """Run write operation with in-memory idempotency.

        Args:
            key: Idempotency key.
            caller: Callable returning ``ReturnResponse``.

        Returns:
            ReturnResponse: Cached or fresh result.
        """
        now = time.time()
        self._cleanup_idempotency_cache(now)
        cached = self._idempotency_cache.get(key)
        if cached and now - cached[0] <= self._idempotency_ttl_seconds:
            return cached[1]
        response = caller()
        if response.code == 0:
            self._idempotency_cache[key] = (now, response)
        return response

    def _cleanup_idempotency_cache(self, now_ts: float) -> None:
        """Remove expired idempotency cache entries.

        Args:
            now_ts: Current timestamp.
        """
        expired_keys = [
            cache_key
            for cache_key, (created_at, _resp) in self._idempotency_cache.items()
            if now_ts - created_at > self._idempotency_ttl_seconds
        ]
        for cache_key in expired_keys:
            self._idempotency_cache.pop(cache_key, None)
