#!/usr/bin/env python3

import time
from typing import Any, Dict

import httpx

from pytbox.feishu.client import Client
from pytbox.schemas.response import ReturnResponse


class DummyHTTPResponse:
    def __init__(
        self,
        status_code: int,
        payload: Dict[str, Any],
        reason_phrase: str = "",
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.reason_phrase = reason_phrase

    def json(self) -> Dict[str, Any]:
        return self._payload


def _mock_token_ok() -> ReturnResponse:
    return ReturnResponse(
        code=0,
        msg="token ok",
        data={"token": "token-1", "expires_at": int(time.time()) + 3600},
    )


def test_request_success_returns_return_response(monkeypatch) -> None:
    client = Client(app_id="app-id", app_secret="app-secret")
    monkeypatch.setattr(client.token_provider, "get_token", _mock_token_ok)

    def fake_send(_request: Any) -> DummyHTTPResponse:
        return DummyHTTPResponse(200, {"code": 0, "msg": "ok", "data": {"x": 1}})

    monkeypatch.setattr(client.client, "send", fake_send)
    result = client.request(path="/im/v1/messages", method="GET")
    assert isinstance(result, ReturnResponse)
    assert result.code == 0
    assert result.data == {"x": 1}


def test_request_retries_on_timeout(monkeypatch) -> None:
    client = Client(app_id="app-id", app_secret="app-secret")
    monkeypatch.setattr(client.token_provider, "get_token", _mock_token_ok)
    monkeypatch.setattr("pytbox.feishu.client.time.sleep", lambda _seconds: None)

    attempts = {"count": 0}

    def fake_send(_request: Any) -> DummyHTTPResponse:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise httpx.TimeoutException("timeout")
        return DummyHTTPResponse(200, {"code": 0, "msg": "ok", "data": {"done": True}})

    monkeypatch.setattr(client.client, "send", fake_send)
    result = client.request(path="/im/v1/messages", method="GET")
    assert result.code == 0
    assert attempts["count"] == 3


def test_request_retries_on_429_then_success(monkeypatch) -> None:
    client = Client(app_id="app-id", app_secret="app-secret")
    monkeypatch.setattr(client.token_provider, "get_token", _mock_token_ok)
    monkeypatch.setattr("pytbox.feishu.client.time.sleep", lambda _seconds: None)

    attempts = {"count": 0}

    def fake_send(_request: Any) -> DummyHTTPResponse:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return DummyHTTPResponse(429, {"code": 429, "msg": "too many requests"})
        return DummyHTTPResponse(200, {"code": 0, "msg": "ok", "data": {"x": 2}})

    monkeypatch.setattr(client.client, "send", fake_send)
    result = client.request(path="/im/v1/messages", method="GET")
    assert result.code == 0
    assert attempts["count"] == 2


def test_request_does_not_retry_on_non_retryable_4xx(monkeypatch) -> None:
    client = Client(app_id="app-id", app_secret="app-secret")
    monkeypatch.setattr(client.token_provider, "get_token", _mock_token_ok)
    monkeypatch.setattr("pytbox.feishu.client.time.sleep", lambda _seconds: None)

    attempts = {"count": 0}

    def fake_send(_request: Any) -> DummyHTTPResponse:
        attempts["count"] += 1
        return DummyHTTPResponse(400, {"code": 1001, "msg": "bad request", "data": {"field": "x"}})

    monkeypatch.setattr(client.client, "send", fake_send)
    result = client.request(path="/im/v1/messages", method="GET")
    assert result.code == 1001
    assert attempts["count"] == 1


def test_request_refreshes_token_once_when_invalid(monkeypatch) -> None:
    client = Client(app_id="app-id", app_secret="app-secret")
    monkeypatch.setattr(client.token_provider, "get_token", _mock_token_ok)
    monkeypatch.setattr("pytbox.feishu.client.time.sleep", lambda _seconds: None)

    refresh_calls = {"count": 0}

    def fake_refresh() -> ReturnResponse:
        refresh_calls["count"] += 1
        return ReturnResponse(
            code=0,
            msg="token refreshed",
            data={"token": "token-2", "expires_at": int(time.time()) + 3600},
        )

    monkeypatch.setattr(client.token_provider, "refresh", fake_refresh)

    attempts = {"count": 0}

    def fake_send(_request: Any) -> DummyHTTPResponse:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return DummyHTTPResponse(200, {"code": 99991663, "msg": "Invalid access token for authorization"})
        return DummyHTTPResponse(200, {"code": 0, "msg": "ok", "data": {"x": 3}})

    monkeypatch.setattr(client.client, "send", fake_send)
    result = client.request(path="/im/v1/messages", method="GET")
    assert result.code == 0
    assert attempts["count"] == 2
    assert refresh_calls["count"] == 1
