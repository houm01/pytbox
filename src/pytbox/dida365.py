#!/usr/bin/env python3

"""Dida365 API client.

This module provides a lightweight Dida365 client with unified
``ReturnResponse`` outputs, retry control, and idempotent write helpers.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Iterator, Literal

import requests
from requests.exceptions import RequestException

from .schemas.response import ReturnResponse


@dataclass
class Task:
    """Task entity returned by list APIs.

    Attributes:
        task_id: Task identifier.
        project_id: Project identifier.
        title: Task title.
        content: Task content/body.
        desc: Task description.
        start_date: Task start time string.
        due_date: Task due time string.
        priority: Human-readable priority label.
        status: Human-readable status label.
        tags: Tag list.
        completed_time: Completion time string.
        assignee: Assignee identifier.
    """

    task_id: str | None
    project_id: str | None
    title: str | None
    content: str | None
    desc: str | None
    start_date: str | None
    due_date: str | None
    priority: str
    status: str
    tags: list[str] | None
    completed_time: str | None
    assignee: int | str | None


class ProcessReturnResponse:
    """Helper for converting numeric codes to readable text."""

    @staticmethod
    def status(status: int | None) -> str:
        """Convert task status code into text.

        Args:
            status: Numeric status code.

        Returns:
            Human-readable task status.
        """
        if status == 0:
            return "进行中"
        if status == 2:
            return "已完成"
        return "未识别"

    @staticmethod
    def priority(priority: int | None) -> str:
        """Convert task priority code into text.

        Args:
            priority: Numeric priority code.

        Returns:
            Human-readable priority label.
        """
        if priority == 1:
            return "低优先级"
        if priority == 3:
            return "中优先级"
        if priority == 5:
            return "高优先级"
        return "未识别"


class Dida365:
    """Dida365 API client with retry and idempotency support."""

    def __init__(
        self,
        access_token: str,
        cookie: str,
        timeout: int = 3,
        max_retries: int = 3,
        retry_backoff_base: float = 0.5,
        idempotency_ttl_seconds: int = 300,
    ) -> None:
        """Initialize a Dida365 client.

        Args:
            access_token: Open API access token.
            cookie: Cookie used by enhancement endpoints.
            timeout: Request timeout in seconds.
            max_retries: Max retry attempts, capped at 3.
            retry_backoff_base: Base seconds for exponential backoff.
            idempotency_ttl_seconds: TTL for in-memory idempotency cache.
        """
        self.access_token = access_token
        self.base_url = "https://api.dida365.com"
        self.cookie = cookie
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }
        self.cookie_headers = {
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Cookie": self.cookie,
        }
        self.timeout = timeout
        self.max_retries = min(max_retries, 3)
        self.retry_backoff_base = retry_backoff_base
        self.idempotency_ttl_seconds = idempotency_ttl_seconds
        self._idempotency_cache: dict[str, tuple[float, ReturnResponse]] = {}
        self.logger = logging.getLogger(__name__)

    def request(
        self,
        api_url: str | None = None,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
    ) -> ReturnResponse:
        """Send a request via token-based headers.

        Args:
            api_url: API path (for example ``/open/v1/project``).
            method: HTTP method.
            payload: Optional JSON payload.

        Returns:
            Standardized ``ReturnResponse``.
        """
        if not api_url:
            return ReturnResponse(code=1, msg="api_url is required", data=None)

        resp = self._request_with_retry(
            method=method,
            api_url=api_url,
            payload=payload,
            use_cookie_headers=False,
            task_id="-",
            target=api_url,
        )
        if resp.code != 0:
            return resp

        body = self._extract_body(resp)
        if "complete" in api_url:
            return ReturnResponse(code=0, msg="success", data=None)
        return ReturnResponse(code=0, msg="success", data=body)

    def task_list(self, project_id: str, enhancement: bool = True) -> Iterator[Task]:
        """List project tasks.

        Args:
            project_id: Project identifier.
            enhancement: Whether to use cookie-based enhancement endpoint.

        Yields:
            ``Task`` objects converted from raw API payloads.
        """
        fetch_resp = self._fetch_task_list(project_id=project_id, enhancement=enhancement)
        if fetch_resp.code != 0:
            return

        tasks_data = fetch_resp.data if isinstance(fetch_resp.data, list) else []
        for task in tasks_data:
            if not isinstance(task, dict):
                continue
            yield self._to_task(task)

    def task_create(
        self,
        project_id: str,
        title: str,
        content: str | None = None,
        tags: list[str] | None = None,
        priority: Literal[1, 3, 5] = 1,
        start_date: datetime | str | None = None,
        start_time_offset: bool = True,
        due_date: datetime | str | None = None,
        kind: str | Literal["NOTE"] | None = "TEXT",
        assignee: int | str | None = None,
        reminder: bool = True,
    ) -> ReturnResponse:
        """Create a task in a project.

        Args:
            project_id: Project identifier.
            title: Task title.
            content: Optional task content.
            tags: Optional tag list.
            priority: Task priority code.
            start_date: Task start time.
            start_time_offset: Whether to apply +3 minute offset.
            due_date: Optional task due time.
            kind: Task kind.
            assignee: Optional assignee identifier.
            reminder: Whether to create immediate reminder.

        Returns:
            Standardized ``ReturnResponse``.
        """
        if not project_id or not title:
            return ReturnResponse(code=1, msg="project_id/title is required", data=None)

        real_start_date = start_date if start_date is not None else datetime.utcnow()
        start_date_format = self._format_datetime(real_start_date, start_time_offset)
        if not start_date_format:
            return ReturnResponse(code=1, msg="invalid start_date", data=None)

        payload: dict[str, Any] = {
            "projectId": project_id,
            "priority": priority,
            "title": title,
            "timeZone": "Asia/Shanghai",
            "kind": kind,
            "startDate": start_date_format,
        }

        if content is not None:
            payload["content"] = content
        if assignee is not None:
            payload["assignee"] = str(assignee)
        if reminder:
            payload["reminders"] = ["TRIGGER:PT0S"]
        if tags:
            payload["tags"] = tags

        due_date_format = self._format_datetime(due_date, False)
        if due_date_format:
            payload["dueDate"] = due_date_format

        idempotency_key = self._build_idempotency_key(
            "task_create",
            [
                project_id,
                title,
                content,
                priority,
                start_date_format,
                due_date_format,
                kind,
                assignee,
                tags,
            ],
        )
        return self._run_idempotent(
            key=idempotency_key,
            caller=lambda: self.request(api_url="/open/v1/task", method="POST", payload=payload),
        )

    def task_complete(self, project_id: str, task_id: str) -> ReturnResponse:
        """Mark a task as completed.

        Args:
            project_id: Project identifier.
            task_id: Task identifier.

        Returns:
            Standardized ``ReturnResponse``.
        """
        if not project_id or not task_id:
            return ReturnResponse(code=1, msg="project_id/task_id is required", data=None)

        idempotency_key = self._build_idempotency_key(
            "task_complete", [project_id, task_id]
        )
        return self._run_idempotent(
            key=idempotency_key,
            caller=lambda: self.request(
                api_url=f"/open/v1/project/{project_id}/task/{task_id}/complete",
                method="POST",
            ),
        )

    def task_get(self, project_id: str, task_id: str) -> ReturnResponse:
        """Get a task detail.

        Args:
            project_id: Project identifier.
            task_id: Task identifier.

        Returns:
            Standardized ``ReturnResponse``.
        """
        if not project_id or not task_id:
            return ReturnResponse(code=1, msg="project_id/task_id is required", data=None)
        return self.request(api_url=f"/open/v1/project/{project_id}/task/{task_id}")

    def task_comments(self, project_id: str, task_id: str) -> ReturnResponse:
        """Get comments of a task.

        Args:
            project_id: Project identifier.
            task_id: Task identifier.

        Returns:
            Standardized ``ReturnResponse``.
        """
        if not project_id or not task_id:
            return ReturnResponse(code=1, msg="project_id/task_id is required", data=None)

        resp = self._request_with_retry(
            method="GET",
            api_url=f"/api/v2/project/{project_id}/task/{task_id}/comments",
            payload=None,
            use_cookie_headers=True,
            task_id=task_id,
            target=f"project/{project_id}/task/{task_id}/comments",
        )
        if resp.code != 0:
            return resp
        return ReturnResponse(code=0, msg="success", data=self._extract_body(resp))

    def task_update(
        self,
        project_id: str | None = None,
        task_id: str | None = None,
        title: str | None = None,
        content: str | None = None,
        priority: int | None = None,
        start_date: str | None = None,
        content_front: bool = False,
    ) -> ReturnResponse:
        """Update a task.

        Args:
            project_id: Project identifier.
            task_id: Task identifier.
            title: Optional updated title.
            content: Optional appended/prepended content.
            priority: Optional priority code.
            start_date: Optional start date string.
            content_front: Whether to prepend new content.

        Returns:
            Standardized ``ReturnResponse``.
        """
        if not project_id or not task_id:
            return ReturnResponse(code=1, msg="project_id/task_id is required", data=None)

        task_get_resp = self.task_get(project_id, task_id)
        if task_get_resp.code != 0:
            return task_get_resp

        exists_content = ""
        if isinstance(task_get_resp.data, dict):
            exists_content = task_get_resp.data.get("content") or ""

        merged_content = content
        if content is None:
            merged_content = exists_content
        elif exists_content:
            merged_content = (
                f"{content}\n{exists_content}"
                if content_front
                else f"{exists_content}\n{content}"
            )

        payload: dict[str, Any] = {
            "projectId": project_id,
            "taskId": task_id,
            "title": title,
            "content": merged_content,
            "priority": priority,
        }
        if start_date:
            payload["startDate"] = start_date

        filtered_payload = {k: v for k, v in payload.items() if v is not None}
        idempotency_key = self._build_idempotency_key(
            "task_update",
            [project_id, task_id, title, merged_content, priority, start_date],
        )
        return self._run_idempotent(
            key=idempotency_key,
            caller=lambda: self.request(
                api_url=f"/open/v1/task/{task_id}",
                method="POST",
                payload=filtered_payload,
            ),
        )

    def get_projects(self) -> ReturnResponse:
        """Get all projects visible to current token.

        Returns:
            Standardized ``ReturnResponse``.
        """
        resp = self.request(api_url="/open/v1/project", method="GET")
        if resp.code == 0 and isinstance(resp.data, list):
            return ReturnResponse(
                code=0,
                msg=f"获取到 {len(resp.data)} 条 project",
                data=resp.data,
            )
        return resp

    def _fetch_task_list(self, project_id: str, enhancement: bool) -> ReturnResponse:
        """Fetch raw task list payloads from selected endpoint.

        Args:
            project_id: Project identifier.
            enhancement: Whether to use cookie-based enhancement endpoint.

        Returns:
            Standardized ``ReturnResponse`` containing list payload.
        """
        if not project_id:
            return ReturnResponse(code=1, msg="project_id is required", data=None)

        if enhancement:
            resp = self._request_with_retry(
                method="GET",
                api_url=f"/api/v2/project/{project_id}/tasks",
                payload=None,
                use_cookie_headers=True,
                task_id="-",
                target=f"project/{project_id}/tasks",
            )
        else:
            resp = self.request(api_url=f"/open/v1/project/{project_id}/data", method="GET")

        if resp.code != 0:
            return resp

        body = self._extract_body(resp)
        if enhancement:
            if not isinstance(body, list):
                return ReturnResponse(code=1, msg="invalid task list payload", data=body)
            return ReturnResponse(code=0, msg="success", data=body)

        if isinstance(body, dict):
            tasks = body.get("tasks", [])
            if isinstance(tasks, list):
                return ReturnResponse(code=0, msg="success", data=tasks)
        return ReturnResponse(code=1, msg="invalid task list payload", data=body)

    def _to_task(self, task: dict[str, Any]) -> Task:
        """Convert a raw task dict to ``Task``.

        Args:
            task: Raw task payload.

        Returns:
            Parsed ``Task`` object.
        """
        return Task(
            task_id=task.get("id"),
            project_id=task.get("projectId"),
            title=task.get("title"),
            content=task.get("content"),
            desc=task.get("desc"),
            start_date=task.get("startDate"),
            due_date=task.get("dueDate"),
            priority=ProcessReturnResponse.priority(task.get("priority")),
            status=ProcessReturnResponse.status(task.get("status")),
            tags=task.get("tags"),
            completed_time=task.get("completedTime"),
            assignee=task.get("assignee"),
        )

    def _format_datetime(
        self, value: datetime | str | None, start_time_offset: bool
    ) -> str | None:
        """Format datetime input to Dida365 time string.

        Args:
            value: Datetime/string input.
            start_time_offset: Whether to apply +3 minute offset.

        Returns:
            Formatted time string or ``None`` when input is invalid.
        """
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if not isinstance(value, datetime):
            return None

        dt = value
        if start_time_offset:
            minute = dt.minute + 3
            dt = dt.replace(minute=59 if minute >= 60 else minute)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.000+0000")

    def _build_idempotency_key(self, operation: str, parts: list[Any]) -> str:
        """Build idempotency key for write operations.

        Args:
            operation: Operation name.
            parts: Key parts to hash.

        Returns:
            Deterministic hash string for current time window.
        """
        window = int(time.time() // self.idempotency_ttl_seconds)
        raw = "|".join(str(item) for item in [operation, window, *parts])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _run_idempotent(
        self, key: str, caller: Callable[[], ReturnResponse]
    ) -> ReturnResponse:
        """Execute a callable with idempotency cache.

        Args:
            key: Idempotency cache key.
            caller: Callable that performs the real operation.

        Returns:
            Cached or fresh ``ReturnResponse``.
        """
        now = time.time()
        self._cleanup_idempotency_cache(now)
        cached = self._idempotency_cache.get(key)
        if cached and now - cached[0] <= self.idempotency_ttl_seconds:
            return cached[1]

        resp = caller()
        if resp.code == 0:
            self._idempotency_cache[key] = (now, resp)
        return resp

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

    def _request_with_retry(
        self,
        method: str,
        api_url: str,
        payload: dict[str, Any] | None,
        use_cookie_headers: bool,
        task_id: str,
        target: str,
    ) -> ReturnResponse:
        """Send HTTP request with retry policy.

        Args:
            method: HTTP method.
            api_url: Relative or absolute URL.
            payload: Optional JSON payload.
            use_cookie_headers: Whether to use cookie headers.
            task_id: Task identifier for logging.
            target: Target path for logging.

        Returns:
            Standardized ``ReturnResponse``.
        """
        headers = self.cookie_headers if use_cookie_headers else self.headers
        url = api_url if api_url.startswith("http") else f"{self.base_url}{api_url}"

        for attempt in range(1, self.max_retries + 1):
            started_at = time.monotonic()
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
                duration_ms = int((time.monotonic() - started_at) * 1000)

                if response.status_code in (429, 500, 502, 503, 504):
                    self._log_step(
                        task_id=task_id,
                        target=target,
                        result=f"retry_http_{response.status_code}",
                        duration_ms=duration_ms,
                    )
                    if attempt < self.max_retries:
                        time.sleep(self.retry_backoff_base * (2 ** (attempt - 1)))
                        continue

                body = self._safe_json(response)
                if 200 <= response.status_code < 300:
                    self._log_step(
                        task_id=task_id,
                        target=target,
                        result=f"http_{response.status_code}",
                        duration_ms=duration_ms,
                    )
                    return ReturnResponse(
                        code=0,
                        msg="success",
                        data={"status_code": response.status_code, "body": body},
                    )

                self._log_step(
                    task_id=task_id,
                    target=target,
                    result=f"http_{response.status_code}",
                    duration_ms=duration_ms,
                )
                return ReturnResponse(
                    code=1,
                    msg=f"request failed: {response.status_code}",
                    data={"status_code": response.status_code, "body": body},
                )
            except RequestException as exc:
                duration_ms = int((time.monotonic() - started_at) * 1000)
                self._log_step(
                    task_id=task_id,
                    target=target,
                    result=f"request_exception_{attempt}",
                    duration_ms=duration_ms,
                )
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_base * (2 ** (attempt - 1)))
                    continue
                return ReturnResponse(
                    code=1,
                    msg="request exception",
                    data={"error": str(exc)},
                )
        return ReturnResponse(code=1, msg="request failed after retries", data=None)

    def _safe_json(self, response: requests.Response) -> Any:
        """Parse response JSON safely.

        Args:
            response: HTTP response object.

        Returns:
            Parsed JSON body, or ``{"text": ...}`` on JSON parse failure.
        """
        try:
            return response.json()
        except ValueError:
            return {"text": response.text}

    def _extract_body(self, resp: ReturnResponse) -> Any:
        """Extract normalized body from wrapped response.

        Args:
            resp: Wrapped ``ReturnResponse``.

        Returns:
            Raw body payload.
        """
        if isinstance(resp.data, dict) and "body" in resp.data:
            return resp.data.get("body")
        return resp.data

    def _log_step(
        self,
        task_id: str,
        target: str,
        result: str,
        duration_ms: int,
    ) -> None:
        """Write structured operation log.

        Args:
            task_id: Task identifier.
            target: Target endpoint/path.
            result: Operation result summary.
            duration_ms: Duration in milliseconds.
        """
        self.logger.info(
            "[dida365] task_id=%s target=%s result=%s duration_ms=%s",
            task_id,
            target,
            result,
            duration_ms,
        )


if __name__ == "__main__":
    pass
