#!/usr/bin/env python3

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
import requests

from pytbox.dida365 import Dida365, Task
from pytbox.schemas.response import ReturnResponse


class DummyResponse:
    def __init__(
        self,
        status_code: int,
        json_data: Any = None,
        text_data: str = "",
        raise_json_error: bool = False,
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data
        self.text = text_data
        self._raise_json_error = raise_json_error

    def json(self) -> Any:
        if self._raise_json_error:
            raise ValueError("invalid json")
        return self._json_data


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pytbox.dida365.time.sleep", lambda _seconds: None)


@pytest.fixture
def dida_client() -> Dida365:
    return Dida365(
        access_token="token-secret-value",
        cookie="cookie-secret-value",
        timeout=1,
        max_retries=3,
        retry_backoff_base=0.1,
        idempotency_ttl_seconds=300,
    )


def test_request_success_json(
    dida_client: Dida365, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "pytbox.dida365.requests.request",
        lambda **_kwargs: DummyResponse(200, {"ok": True}),
    )

    resp = dida_client.request(api_url="/open/v1/project", method="GET")

    assert isinstance(resp, ReturnResponse)
    assert resp.code == 0
    assert resp.data == {"ok": True}


def test_request_non_json_payload(
    dida_client: Dida365, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "pytbox.dida365.requests.request",
        lambda **_kwargs: DummyResponse(
            200, json_data=None, text_data="raw text", raise_json_error=True
        ),
    )

    resp = dida_client.request(api_url="/open/v1/project", method="GET")

    assert resp.code == 0
    assert resp.data == {"text": "raw text"}


def test_request_retry_on_5xx_then_success(
    dida_client: Dida365, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []

    def fake_request(**_kwargs: Any) -> DummyResponse:
        calls.append(1)
        if len(calls) < 3:
            return DummyResponse(500, {"error": "server down"})
        return DummyResponse(200, {"ok": 1})

    monkeypatch.setattr("pytbox.dida365.requests.request", fake_request)

    resp = dida_client.request(api_url="/open/v1/project", method="GET")

    assert resp.code == 0
    assert resp.data == {"ok": 1}
    assert len(calls) == 3


def test_request_no_retry_on_4xx(
    dida_client: Dida365, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []

    def fake_request(**_kwargs: Any) -> DummyResponse:
        calls.append(1)
        return DummyResponse(400, {"error": "bad request"})

    monkeypatch.setattr("pytbox.dida365.requests.request", fake_request)

    resp = dida_client.request(api_url="/open/v1/project", method="GET")

    assert resp.code == 1
    assert len(calls) == 1


def test_request_retry_on_timeout(
    dida_client: Dida365, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []

    def fake_request(**_kwargs: Any) -> DummyResponse:
        calls.append(1)
        if len(calls) < 3:
            raise requests.exceptions.Timeout("timeout")
        return DummyResponse(200, {"ok": "retry-success"})

    monkeypatch.setattr("pytbox.dida365.requests.request", fake_request)

    resp = dida_client.request(api_url="/open/v1/project", method="GET")

    assert resp.code == 0
    assert resp.data == {"ok": "retry-success"}
    assert len(calls) == 3


def test_task_list_enhancement_true(
    dida_client: Dida365, monkeypatch: pytest.MonkeyPatch
) -> None:
    task_payload = [
        {
            "id": "t-1",
            "projectId": "p-1",
            "title": "task-title",
            "content": "task-content",
            "status": 0,
            "priority": 3,
        }
    ]
    monkeypatch.setattr(
        "pytbox.dida365.requests.request",
        lambda **_kwargs: DummyResponse(200, task_payload),
    )

    tasks = list(dida_client.task_list(project_id="p-1", enhancement=True))

    assert len(tasks) == 1
    assert isinstance(tasks[0], Task)
    assert tasks[0].task_id == "t-1"
    assert tasks[0].status == "进行中"
    assert tasks[0].priority == "中优先级"


def test_task_list_enhancement_false(
    dida_client: Dida365, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "pytbox.dida365.requests.request",
        lambda **_kwargs: DummyResponse(
            200, {"tasks": [{"id": "t-2", "projectId": "p-2", "status": 2, "priority": 1}]}
        ),
    )

    tasks = list(dida_client.task_list(project_id="p-2", enhancement=False))

    assert len(tasks) == 1
    assert tasks[0].task_id == "t-2"
    assert tasks[0].status == "已完成"
    assert tasks[0].priority == "低优先级"


def test_task_create_idempotent(
    dida_client: Dida365, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_request(**kwargs: Any) -> DummyResponse:
        calls.append(kwargs)
        return DummyResponse(200, {"id": "new-task"})

    monkeypatch.setattr("pytbox.dida365.requests.request", fake_request)

    start_at = datetime(2026, 2, 1, 8, 10, 0)
    first = dida_client.task_create(project_id="p-1", title="create", start_date=start_at)
    second = dida_client.task_create(project_id="p-1", title="create", start_date=start_at)

    assert first.code == 0
    assert second.code == 0
    assert first.data == {"id": "new-task"}
    assert len(calls) == 1


def test_task_complete_idempotent(
    dida_client: Dida365, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []

    def fake_request(**_kwargs: Any) -> DummyResponse:
        calls.append(1)
        return DummyResponse(200, {"ok": True})

    monkeypatch.setattr("pytbox.dida365.requests.request", fake_request)

    first = dida_client.task_complete(project_id="p-1", task_id="t-1")
    second = dida_client.task_complete(project_id="p-1", task_id="t-1")

    assert first.code == 0
    assert second.code == 0
    assert len(calls) == 1


def test_task_get_returns_return_response(
    dida_client: Dida365, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "pytbox.dida365.requests.request",
        lambda **_kwargs: DummyResponse(200, {"id": "t-1", "content": "old"}),
    )

    resp = dida_client.task_get(project_id="p-1", task_id="t-1")

    assert isinstance(resp, ReturnResponse)
    assert resp.code == 0
    assert resp.data["id"] == "t-1"


def test_task_comments_returns_return_response(
    dida_client: Dida365, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "pytbox.dida365.requests.request",
        lambda **_kwargs: DummyResponse(200, [{"id": "c-1", "text": "comment"}]),
    )

    resp = dida_client.task_comments(project_id="p-1", task_id="t-1")

    assert isinstance(resp, ReturnResponse)
    assert resp.code == 0
    assert isinstance(resp.data, list)
    assert resp.data[0]["id"] == "c-1"


def test_task_update_merges_content(
    dida_client: Dida365, monkeypatch: pytest.MonkeyPatch
) -> None:
    payloads: list[dict[str, Any] | None] = []

    def fake_request(**kwargs: Any) -> DummyResponse:
        method = kwargs.get("method")
        url = kwargs.get("url", "")
        if method == "GET" and "/open/v1/project/p-1/task/t-1" in url:
            return DummyResponse(200, {"id": "t-1", "content": "exists"})
        if method == "POST" and "/open/v1/task/t-1" in url:
            payloads.append(kwargs.get("json"))
            return DummyResponse(200, {"id": "t-1", "updated": True})
        raise AssertionError(f"unexpected request: method={method}, url={url}")

    monkeypatch.setattr("pytbox.dida365.requests.request", fake_request)

    resp = dida_client.task_update(
        project_id="p-1",
        task_id="t-1",
        content="new-content",
        content_front=False,
    )

    assert resp.code == 0
    assert payloads
    assert payloads[0]["content"] == "exists\nnew-content"


def test_get_projects_success(
    dida_client: Dida365, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "pytbox.dida365.requests.request",
        lambda **_kwargs: DummyResponse(200, [{"id": "p1"}, {"id": "p2"}]),
    )

    resp = dida_client.get_projects()

    assert resp.code == 0
    assert "2" in resp.msg
    assert len(resp.data) == 2


def test_logs_do_not_include_secrets(
    dida_client: Dida365,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO")
    monkeypatch.setattr(
        "pytbox.dida365.requests.request",
        lambda **_kwargs: DummyResponse(200, {"ok": True}),
    )

    _ = dida_client.request(api_url="/open/v1/project", method="GET")

    assert "token-secret-value" not in caplog.text
    assert "cookie-secret-value" not in caplog.text
    assert "Authorization" not in caplog.text
