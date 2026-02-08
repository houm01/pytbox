#!/usr/bin/env python3

"""Unit tests for Victorialog."""

from __future__ import annotations

from typing import Any

import pytest
from requests.exceptions import Timeout

from pytbox.log.victorialog import Victorialog
from pytbox.schemas.response import ReturnResponse


class DummyHTTPResponse:
    """Simple fake HTTP response."""

    def __init__(self, status_code: int, text: str) -> None:
        """Initialize response.

        Args:
            status_code: HTTP status code.
            text: Raw response body.
        """
        self.status_code = status_code
        self.text = text


def test_send_program_log_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Retryable HTTP errors should retry then succeed."""
    responses = [DummyHTTPResponse(503, "busy"), DummyHTTPResponse(200, "ok")]
    post_calls: list[dict[str, Any]] = []

    def fake_post(**kwargs: Any) -> DummyHTTPResponse:
        post_calls.append(kwargs)
        return responses.pop(0)

    monkeypatch.setattr("pytbox.log.victorialog.requests.post", fake_post)
    monkeypatch.setattr("pytbox.log.victorialog.time.sleep", lambda _s: None)

    client = Victorialog(url="https://vl.example.com", timeout=9, max_retries=3, retry_backoff_base=0.1)
    response = client.send_program_log(level="WARN", message="hello")

    assert isinstance(response, ReturnResponse)
    assert response.code == 0
    assert len(post_calls) == 2
    assert post_calls[0]["timeout"] == 9
    assert post_calls[0]["json"]["log"]["level"] == "WARNING"


def test_send_program_log_returns_fail_after_exception_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Request exceptions should retry up to max_retries and fail."""
    post_calls: list[dict[str, Any]] = []

    def fake_post(**kwargs: Any) -> DummyHTTPResponse:
        post_calls.append(kwargs)
        raise Timeout("boom")

    monkeypatch.setattr("pytbox.log.victorialog.requests.post", fake_post)
    monkeypatch.setattr("pytbox.log.victorialog.time.sleep", lambda _s: None)

    client = Victorialog(url="https://vl.example.com", timeout=3, max_retries=3, retry_backoff_base=0.1)
    response = client.send_program_log(level="INFO", message="hello")

    assert response.code == 1
    assert len(post_calls) == 3


def test_query_returns_no_data_when_empty_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """Query should return code=2 when response text is empty."""
    monkeypatch.setattr(
        "pytbox.log.victorialog.requests.post",
        lambda **_kwargs: DummyHTTPResponse(200, ""),
    )
    monkeypatch.setattr("pytbox.log.victorialog.time.sleep", lambda _s: None)

    client = Victorialog(url="https://vl.example.com")
    response = client.query(query="stream:app")

    assert isinstance(response, ReturnResponse)
    assert response.code == 2


def test_query_honors_delay_and_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Query should sleep for delay and pass configured timeout."""
    sleep_calls: list[float] = []
    post_calls: list[dict[str, Any]] = []

    monkeypatch.setattr("pytbox.log.victorialog.time.sleep", lambda sec: sleep_calls.append(sec))

    def fake_post(**kwargs: Any) -> DummyHTTPResponse:
        post_calls.append(kwargs)
        return DummyHTTPResponse(200, "line-1")

    monkeypatch.setattr("pytbox.log.victorialog.requests.post", fake_post)

    client = Victorialog(url="https://vl.example.com", timeout=6)
    response = client.query(query="app:test", delay=2)

    assert response.code == 0
    assert response.data == "line-1"
    assert sleep_calls[0] == 2
    assert post_calls[0]["timeout"] == 6


def test_send_syslog_is_idempotent_within_window(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same syslog payload in one idempotency window should be sent once."""
    post_calls: list[dict[str, Any]] = []

    def fake_post(**kwargs: Any) -> DummyHTTPResponse:
        post_calls.append(kwargs)
        return DummyHTTPResponse(200, "ok")

    monkeypatch.setattr("pytbox.log.victorialog.requests.post", fake_post)
    monkeypatch.setattr("pytbox.log.victorialog.time.sleep", lambda _s: None)

    client = Victorialog(url="https://vl.example.com", idempotency_ttl_seconds=300)
    first = client.send_syslog(
        stream="automation",
        hostname="host-a",
        ip="1.1.1.1",
        level="INFO",
        message="same",
        date="2026-02-08T10:00:00Z",
    )
    second = client.send_syslog(
        stream="automation",
        hostname="host-a",
        ip="1.1.1.1",
        level="INFO",
        message="same",
        date="2026-02-08T10:00:00Z",
    )

    assert first.code == 0
    assert second.code == 0
    assert len(post_calls) == 1
