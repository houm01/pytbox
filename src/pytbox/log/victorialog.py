#!/usr/bin/env python3

"""VictoriaLogs client with retry, timeout, and idempotent writes."""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from typing import Any, Callable, Literal

import requests
from requests.exceptions import RequestException

from ..schemas.response import ReturnResponse
from ..utils.timeutils import TimeUtils


RetryLevel = Literal[
    "INFO",
    "DEBUG",
    "WARNING",
    "WARN",
    "ERROR",
    "CRITICAL",
    "SUCCESS",
    "EXCEPTION",
]


class Victorialog:
    """VictoriaLogs API wrapper."""

    def __init__(
        self,
        url: str | None = None,
        timeout: int = 3,
        max_retries: int = 3,
        retry_backoff_base: float = 0.5,
        idempotency_ttl_seconds: int = 300,
    ) -> None:
        """Initialize a VictoriaLogs client.

        Args:
            url: VictoriaLogs base URL.
            timeout: HTTP timeout in seconds.
            max_retries: Maximum retry count, capped at 3.
            retry_backoff_base: Exponential backoff base in seconds.
            idempotency_ttl_seconds: In-memory idempotency TTL for write requests.
        """
        self.url = url.rstrip("/") if url else None
        self.timeout = timeout
        self.max_retries = min(max_retries, 3)
        self.retry_backoff_base = retry_backoff_base
        self.idempotency_ttl_seconds = idempotency_ttl_seconds
        self._idempotency_cache: dict[str, tuple[float, ReturnResponse]] = {}
        self._logger = logging.getLogger(__name__)

    def send_program_log(
        self,
        stream: str = "inbox",
        date: str | None = None,
        level: RetryLevel = "INFO",
        message: str = "test",
        app_name: str = "test",
        file_name: str | None = None,
        line_number: int | None = None,
        function_name: str | None = None,
    ) -> ReturnResponse:
        """Send a program log to VictoriaLogs.

        Args:
            stream: VictoriaLogs stream field.
            date: Timestamp string in UTC. Uses current UTC when omitted.
            level: Log level.
            message: Log message.
            app_name: App name.
            file_name: Source file path.
            line_number: Source line number.
            function_name: Source function name.

        Returns:
            ReturnResponse: Send result.
        """
        if not self.url:
            return ReturnResponse(code=1, msg="victorialog url is required", data=None)

        normalized_message = self._safe_str(message)
        payload = {
            "log": {
                "level": self._normalize_level(level),
                "message": normalized_message,
                "app": app_name,
                "file": file_name,
                "line": line_number,
                "function": function_name,
            },
            "date": date or TimeUtils.get_utc_time(),
            "stream": stream,
        }
        idempotency_key = self._build_idempotency_key("send_program_log", payload)
        result = self._run_idempotent(
            key=idempotency_key,
            caller=lambda: self._post_with_retry(
                target="/insert/jsonline?_stream_fields=stream&_time_field=date&_msg_field=log.message",
                headers={"Content-Type": "application/stream+json"},
                json_payload=payload,
            ),
        )
        if result.code == 0:
            return ReturnResponse(code=0, msg=f"{normalized_message} 发送成功", data=result.data)
        return ReturnResponse(code=1, msg=f"{normalized_message} 发送失败", data=result.data)

    def send_syslog(
        self,
        stream: str,
        hostname: str,
        ip: str,
        level: RetryLevel,
        message: str,
        date: str | None = None,
    ) -> ReturnResponse:
        """Send a syslog event.

        Args:
            stream: VictoriaLogs stream field.
            hostname: Hostname.
            ip: IP address.
            level: Syslog level.
            message: Log message.
            date: Timestamp string in UTC. Uses current UTC when omitted.

        Returns:
            ReturnResponse: Send result.
        """
        if not self.url:
            return ReturnResponse(code=1, msg="victorialog url is required", data=None)

        normalized_message = self._safe_str(message)
        payload = {
            "log": {
                "hostname": hostname,
                "ip": ip,
                "level": self._normalize_level(level),
                "message": normalized_message,
            },
            "date": date or TimeUtils.get_utc_time(),
            "stream": stream,
        }
        idempotency_key = self._build_idempotency_key("send_syslog", payload)
        result = self._run_idempotent(
            key=idempotency_key,
            caller=lambda: self._post_with_retry(
                target="",
                headers={"Content-Type": "application/stream+json"},
                json_payload=payload,
            ),
        )
        if result.code == 0:
            return ReturnResponse(code=0, msg=f"{normalized_message} 发送成功", data=result.data)
        return ReturnResponse(code=1, msg=f"{normalized_message} 发送失败", data=result.data)

    def query(self, query: str | None = None, delay: int = 0) -> ReturnResponse:
        """Query logs from VictoriaLogs.

        Args:
            query: LogSQL query text.
            delay: Delay in seconds before request.

        Returns:
            ReturnResponse: Query result.
        """
        if not self.url:
            return ReturnResponse(code=1, msg="victorialog url is required", data=None)

        form_data = {"query": query}
        if delay > 0:
            time.sleep(delay)

        response = self._post_with_retry(
            target="/select/logsql/query",
            form_data=form_data,
        )
        if response.code != 0:
            return ReturnResponse(code=1, msg=f"{form_data} 查询失败", data=response.data)

        response_text = ""
        if isinstance(response.data, dict):
            response_text = str(response.data.get("text") or "")

        if response_text:
            return ReturnResponse(code=0, msg=f"{form_data} 查询成功", data=response_text)
        return ReturnResponse(code=2, msg=f"{form_data} 查询成功, 但没有数据", data=None)

    def _post_with_retry(
        self,
        target: str,
        headers: dict[str, str] | None = None,
        json_payload: dict[str, Any] | None = None,
        form_data: dict[str, Any] | None = None,
    ) -> ReturnResponse:
        """Execute HTTP POST with timeout and retry policy.

        Args:
            target: URL path relative to base URL.
            headers: Optional request headers.
            json_payload: Optional JSON payload.
            form_data: Optional form payload.

        Returns:
            ReturnResponse: Request result.
        """
        if not self.url:
            return ReturnResponse(code=1, msg="victorialog url is required", data=None)

        full_url = f"{self.url}{target}"
        task_id = uuid.uuid4().hex[:8]
        for attempt in range(1, self.max_retries + 1):
            started_at = time.monotonic()
            try:
                response = requests.post(
                    url=full_url,
                    headers=headers,
                    json=json_payload,
                    data=form_data,
                    timeout=self.timeout,
                )
                duration_ms = int((time.monotonic() - started_at) * 1000)
                if response.status_code in (429, 500, 502, 503, 504):
                    self._log_step(
                        task_id=task_id,
                        target=target or "/",
                        result=f"retry_http_{response.status_code}",
                        duration_ms=duration_ms,
                    )
                    if attempt < self.max_retries:
                        time.sleep(self.retry_backoff_base * (2 ** (attempt - 1)))
                        continue

                self._log_step(
                    task_id=task_id,
                    target=target or "/",
                    result=f"http_{response.status_code}",
                    duration_ms=duration_ms,
                )
                if 200 <= response.status_code < 300:
                    return ReturnResponse(
                        code=0,
                        msg="request success",
                        data={"status_code": response.status_code, "text": response.text},
                    )
                return ReturnResponse(
                    code=1,
                    msg=f"request failed: {response.status_code}",
                    data={"status_code": response.status_code, "text": response.text},
                )
            except RequestException as exc:
                duration_ms = int((time.monotonic() - started_at) * 1000)
                result = f"request_exception_{attempt}"
                if attempt < self.max_retries:
                    self._log_step(
                        task_id=task_id,
                        target=target or "/",
                        result=result,
                        duration_ms=duration_ms,
                    )
                    time.sleep(self.retry_backoff_base * (2 ** (attempt - 1)))
                    continue
                self._log_step(
                    task_id=task_id,
                    target=target or "/",
                    result="request_exception_final",
                    duration_ms=duration_ms,
                )
                return ReturnResponse(
                    code=1,
                    msg="request exception",
                    data={"error": str(exc)},
                )
        return ReturnResponse(code=1, msg="request failed after retries", data=None)

    def _safe_str(self, message: Any) -> str:
        """Convert arbitrary message into string safely.

        Args:
            message: Raw message value.

        Returns:
            str: Converted message string.
        """
        if isinstance(message, str):
            return message
        try:
            return str(message)
        except Exception:
            return "message 无法转换为字符串"

    def _normalize_level(self, level: RetryLevel | str) -> str:
        """Normalize level aliases used by callers.

        Args:
            level: Raw level value.

        Returns:
            str: Normalized level value.
        """
        upper_level = str(level).upper()
        mapping = {
            "WARN": "WARNING",
            "EXCEPTION": "ERROR",
        }
        return mapping.get(upper_level, upper_level)

    def _build_idempotency_key(self, operation: str, payload: dict[str, Any]) -> str:
        """Build an idempotency key for write operations.

        Args:
            operation: Operation name.
            payload: Request payload.

        Returns:
            str: Idempotency key.
        """
        window = int(time.time() // self.idempotency_ttl_seconds)
        body = json.dumps(payload, sort_keys=True, default=str)
        raw = f"{operation}|{window}|{body}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _run_idempotent(
        self,
        key: str,
        caller: Callable[[], ReturnResponse],
    ) -> ReturnResponse:
        """Run write call with in-memory idempotency.

        Args:
            key: Idempotency key.
            caller: Callable returning ReturnResponse.

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
        """Write key-step reliability logs without sensitive data.

        Args:
            task_id: Task identifier.
            target: External call target.
            result: Result summary.
            duration_ms: Duration in milliseconds.
        """
        self._logger.info(
            "[victorialog] task_id=%s target=%s result=%s duration_ms=%s",
            task_id,
            target,
            result,
            duration_ms,
        )


if __name__ == "__main__":
    pass
