#!/usr/bin/env python3

"""Request-layer contract tests for NetBox client."""

from __future__ import annotations

from typing import Any

import pytest
from requests.exceptions import Timeout

from pytbox.netbox.client import NetboxClient
from pytbox.schemas.response import ReturnResponse


class DummyHTTPResponse:
    """Simple mock HTTP response."""

    def __init__(self, status_code: int, payload: Any, text: str = "") -> None:
        """Initialize a dummy response.

        Args:
            status_code: HTTP status code.
            payload: JSON payload.
            text: Raw text fallback.
        """
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> Any:
        """Return payload.

        Returns:
            Any: Stored payload.
        """
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> NetboxClient:
    """Create test client.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        NetboxClient: Initialized client.
    """
    monkeypatch.setattr("pytbox.netbox.client.pynetbox.api", lambda *_args, **_kwargs: object())
    return NetboxClient(
        url="https://netbox.example.com",
        token="token-secret",
        timeout=1,
        max_retries=3,
        retry_backoff_base=0.1,
    )


def test_request_with_retry_retries_on_5xx_then_success(
    client: NetboxClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retry should happen for retryable 5xx errors."""
    calls: list[int] = []

    def fake_request(**_kwargs: Any) -> DummyHTTPResponse:
        calls.append(1)
        if len(calls) < 3:
            return DummyHTTPResponse(status_code=503, payload={"err": "down"})
        return DummyHTTPResponse(status_code=200, payload={"ok": True})

    monkeypatch.setattr("pytbox.netbox.client.time.sleep", lambda _s: None)
    monkeypatch.setattr("pytbox.netbox.client.requests.request", fake_request)

    response = client._request_with_retry("GET", "/api/dcim/sites/")

    assert isinstance(response, ReturnResponse)
    assert response.code == 0
    assert response.data == {"ok": True}
    assert len(calls) == 3


def test_request_with_retry_does_not_retry_on_4xx(
    client: NetboxClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retry should not happen for non-retryable 4xx errors."""
    calls: list[int] = []

    def fake_request(**_kwargs: Any) -> DummyHTTPResponse:
        calls.append(1)
        return DummyHTTPResponse(status_code=400, payload={"err": "bad request"})

    monkeypatch.setattr("pytbox.netbox.client.time.sleep", lambda _s: None)
    monkeypatch.setattr("pytbox.netbox.client.requests.request", fake_request)

    response = client._request_with_retry("GET", "/api/dcim/sites/")

    assert response.code == 1
    assert len(calls) == 1


def test_request_with_retry_retries_on_timeout(
    client: NetboxClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retry should happen for timeout exceptions."""
    calls: list[int] = []

    def fake_request(**_kwargs: Any) -> DummyHTTPResponse:
        calls.append(1)
        if len(calls) < 3:
            raise Timeout("timeout")
        return DummyHTTPResponse(status_code=200, payload={"ok": "done"})

    monkeypatch.setattr("pytbox.netbox.client.time.sleep", lambda _s: None)
    monkeypatch.setattr("pytbox.netbox.client.requests.request", fake_request)

    response = client._request_with_retry("GET", "/api/dcim/sites/")

    assert response.code == 0
    assert response.data == {"ok": "done"}
    assert len(calls) == 3


def test_request_logs_key_fields_without_secrets(
    client: NetboxClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Request logs should include key fields and avoid secrets."""
    monkeypatch.setattr(
        "pytbox.netbox.client.requests.request",
        lambda **_kwargs: DummyHTTPResponse(status_code=200, payload={"ok": 1}),
    )
    caplog.set_level("INFO")

    response = client._request_with_retry("GET", "/api/dcim/regions/")

    assert response.code == 0
    text = caplog.text
    assert "task_id=" in text
    assert "target=/api/dcim/regions/" in text
    assert "duration_ms=" in text
    assert "token-secret" not in text
