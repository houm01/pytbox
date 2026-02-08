#!/usr/bin/env python3

"""AliCloud SLS client with retry, timeout, and idempotent writes."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import hashlib
import json
import logging
import time
import uuid
from typing import Any, Callable, Iterator, Literal

from ..schemas.response import ReturnResponse

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


class AliCloudSls:
    """AliCloud SLS wrapper."""

    def __init__(
        self,
        access_key_id: str | None = None,
        access_key_secret: str | None = None,
        project: str | None = None,
        logstore: str | None = None,
        env: str = "prod",
        timeout: int = 3,
        max_retries: int = 3,
        retry_backoff_base: float = 0.5,
        idempotency_ttl_seconds: int = 300,
    ) -> None:
        """Initialize an SLS client.

        Args:
            access_key_id: Access key id.
            access_key_secret: Access key secret.
            project: SLS project name.
            logstore: SLS logstore name.
            env: Runtime environment label.
            timeout: Timeout in seconds for each SLS write/read call.
            max_retries: Maximum retry count, capped at 3.
            retry_backoff_base: Exponential backoff base in seconds.
            idempotency_ttl_seconds: In-memory idempotency TTL for write operations.
        """
        self.endpoint = "cn-shanghai.log.aliyuncs.com"
        self.project = project
        self.logstore = logstore
        self.env = env
        self.timeout = timeout
        self.max_retries = min(max_retries, 3)
        self.retry_backoff_base = retry_backoff_base
        self.idempotency_ttl_seconds = idempotency_ttl_seconds
        self._idempotency_cache: dict[str, tuple[float, ReturnResponse]] = {}
        self._logger = logging.getLogger(__name__)

        if SlsLogClient is None:
            self.client = None
        else:
            self.client = SlsLogClient(
                self.endpoint,
                access_key_id,
                access_key_secret,
                auth_version=AUTH_VERSION_4,
                region="cn-shanghai",
            )

    def get_logs(
        self,
        project_name: str,
        logstore_name: str,
        query: str,
        from_time: int,
        to_time: int,
    ) -> Iterator[Any]:
        """Get logs from SLS.

        Args:
            project_name: SLS project name.
            logstore_name: SLS logstore name.
            query: Query expression.
            from_time: Query start unix timestamp.
            to_time: Query end unix timestamp.

        Yields:
            Any: Log item content from SLS SDK response.

        Raises:
            RuntimeError: When SDK dependency is unavailable or request fails.
        """
        if GetLogsRequest is None or self.client is None:
            raise RuntimeError("aliyun-log-python-sdk is required")

        request = GetLogsRequest(project_name, logstore_name, from_time, to_time, query=query)
        response = self._request_with_retry(
            operation="get_logs",
            target=f"{project_name}/{logstore_name}",
            caller=lambda: self._invoke_with_timeout(self.client.get_logs, request),
        )
        if response.code != 0:
            raise RuntimeError(response.msg)
        raw_response = response.data
        logs = raw_response.get_logs() if raw_response is not None else []
        for log in logs:
            yield log.contents

    def put_logs(
        self,
        topic: Literal["meraki_alert", "program"] = "program",
        level: Literal["INFO", "WARN", "WARNING", "DEBUG", "ERROR", "CRITICAL", "EXCEPTION"] = "INFO",
        msg: str | None = None,
        app: str | None = None,
        caller_filename: str | None = None,
        caller_lineno: int | None = None,
        caller_function: str | None = None,
        call_full_filename: str | None = None,
    ) -> ReturnResponse:
        """Write program logs into SLS.

        Args:
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
        if self.client is None or LogItem is None or PutLogsRequest is None:
            return ReturnResponse(code=1, msg="aliyun-log-python-sdk is required", data=None)

        normalized_level = level
        if level == "WARN":
            normalized_level = "WARNING"
        if level == "EXCEPTION":
            normalized_level = "ERROR"
        contents = [
            ("env", self.env),
            ("level", normalized_level),
            ("app", app),
            ("msg", msg),
            ("caller_filename", caller_filename),
            ("caller_lineno", str(caller_lineno)),
            ("caller_function", caller_function),
            ("call_full_filename", call_full_filename),
        ]
        payload = {
            "topic": topic,
            "contents": contents,
            "project": self.project,
            "logstore": self.logstore,
        }
        key = self._build_idempotency_key("put_logs", payload)
        return self._run_idempotent(
            key=key,
            caller=lambda: self._put_logs_once(topic=topic, contents=contents),
        )

    def put_logs_for_meraki(self, alert: list[tuple[str, Any]]) -> ReturnResponse:
        """Write Meraki alert logs into SLS.

        Args:
            alert: Key-value tuple list expected by SLS ``LogItem.set_contents``.

        Returns:
            ReturnResponse: Write result.
        """
        if self.client is None or LogItem is None or PutLogsRequest is None:
            return ReturnResponse(code=1, msg="aliyun-log-python-sdk is required", data=None)

        payload = {
            "topic": "",
            "contents": alert,
            "project": self.project,
            "logstore": self.logstore,
        }
        key = self._build_idempotency_key("put_logs_for_meraki", payload)
        return self._run_idempotent(
            key=key,
            caller=lambda: self._put_logs_once(topic="", contents=alert),
        )

    def _put_logs_once(self, topic: str, contents: list[tuple[str, Any]]) -> ReturnResponse:
        """Build and send a single SLS PutLogs request with retry.

        Args:
            topic: SLS topic.
            contents: SLS log contents.

        Returns:
            ReturnResponse: Write result.
        """
        if LogItem is None or PutLogsRequest is None or self.client is None:
            return ReturnResponse(code=1, msg="aliyun-log-python-sdk is required", data=None)

        log_group: list[Any] = []
        log_item = LogItem()
        log_item.set_contents(contents)
        log_group.append(log_item)
        request = PutLogsRequest(self.project, self.logstore, topic, "", log_group, compress=False)
        return self._request_with_retry(
            operation="put_logs",
            target=f"{self.project}/{self.logstore}",
            caller=lambda: self._invoke_with_timeout(self.client.put_logs, request),
        )

    def _request_with_retry(
        self,
        operation: str,
        target: str,
        caller: Callable[[], Any],
    ) -> ReturnResponse:
        """Run SLS operation with retries and structured logs.

        Args:
            operation: Operation name.
            target: External call target.
            caller: Callable to execute.

        Returns:
            ReturnResponse: Operation result.
        """
        task_id = uuid.uuid4().hex[:8]
        for attempt in range(1, self.max_retries + 1):
            started_at = time.monotonic()
            try:
                response = caller()
                duration_ms = int((time.monotonic() - started_at) * 1000)
                self._log_step(
                    task_id=task_id,
                    target=target,
                    result=f"{operation}_ok",
                    duration_ms=duration_ms,
                )
                return ReturnResponse(code=0, msg="sls request success", data=response)
            except FutureTimeoutError:
                duration_ms = int((time.monotonic() - started_at) * 1000)
                result = f"{operation}_timeout_retry" if attempt < self.max_retries else f"{operation}_timeout_fail"
                self._log_step(task_id=task_id, target=target, result=result, duration_ms=duration_ms)
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_base * (2 ** (attempt - 1)))
                    continue
                return ReturnResponse(
                    code=1,
                    msg=f"{operation} timeout",
                    data={"target": target},
                )
            except Exception as exc:
                duration_ms = int((time.monotonic() - started_at) * 1000)
                result = f"{operation}_retry" if attempt < self.max_retries else f"{operation}_fail"
                self._log_step(task_id=task_id, target=target, result=result, duration_ms=duration_ms)
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_base * (2 ** (attempt - 1)))
                    continue
                return ReturnResponse(
                    code=1,
                    msg=f"{operation} failed",
                    data={"error": str(exc)},
                )
        return ReturnResponse(code=1, msg=f"{operation} failed after retries", data=None)

    def _invoke_with_timeout(self, caller: Callable[..., Any], *args: Any) -> Any:
        """Invoke SDK call with timeout guard.

        Args:
            caller: Callable to execute.
            *args: Positional arguments for callable.

        Returns:
            Any: Callable return value.

        Raises:
            FutureTimeoutError: When execution timeout is exceeded.
            Exception: Any exception raised by callable.
        """
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(caller, *args)
            return future.result(timeout=self.timeout)

    def _build_idempotency_key(self, operation: str, payload: dict[str, Any]) -> str:
        """Build an idempotency key for write operations.

        Args:
            operation: Operation name.
            payload: Request payload.

        Returns:
            str: Idempotency key.
        """
        window = int(time.time() // self.idempotency_ttl_seconds)
        raw = f"{operation}|{window}|{json.dumps(payload, sort_keys=True, default=str)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _run_idempotent(self, key: str, caller: Callable[[], ReturnResponse]) -> ReturnResponse:
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
        if cached and now - cached[0] <= self.idempotency_ttl_seconds:
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
            if now_ts - created_at > self.idempotency_ttl_seconds
        ]
        for cache_key in expired_keys:
            self._idempotency_cache.pop(cache_key, None)

    def _log_step(
        self,
        task_id: str,
        target: str,
        result: str,
        duration_ms: int,
    ) -> None:
        """Write key-step reliability logs without secrets.

        Args:
            task_id: Task identifier.
            target: External call target.
            result: Result summary.
            duration_ms: Duration in milliseconds.
        """
        self._logger.info(
            "[sls] task_id=%s target=%s result=%s duration_ms=%s",
            task_id,
            target,
            result,
            duration_ms,
        )


if __name__ == "__main__":
    pass
