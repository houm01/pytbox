#!/usr/bin/env python3

"""Unit tests for AliCloudSls."""

from __future__ import annotations

from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any

import pytest

from pytbox.alicloud import sls as sls_module
from pytbox.alicloud.sls import AliCloudSls
from pytbox.schemas.response import ReturnResponse


class FakeLogItem:
    """Fake SLS log item."""

    def __init__(self) -> None:
        """Initialize fake log item."""
        self.contents: list[tuple[str, Any]] = []

    def set_contents(self, contents: list[tuple[str, Any]]) -> None:
        """Set item contents.

        Args:
            contents: Log contents.
        """
        self.contents = contents


class FakePutLogsRequest:
    """Fake PutLogsRequest."""

    def __init__(
        self,
        project: str | None,
        logstore: str | None,
        topic: str,
        source: str,
        log_group: list[FakeLogItem],
        compress: bool = False,
    ) -> None:
        """Initialize request object.

        Args:
            project: Project name.
            logstore: Logstore name.
            topic: Topic field.
            source: Source field.
            log_group: Grouped log items.
            compress: Compression flag.
        """
        self.project = project
        self.logstore = logstore
        self.topic = topic
        self.source = source
        self.log_group = log_group
        self.compress = compress


class FakeSlsClient:
    """Fake SLS client with scripted responses."""

    def __init__(self, scripted_results: list[Any] | None = None) -> None:
        """Initialize fake client.

        Args:
            scripted_results: Sequence of responses or exceptions.
        """
        self.scripted_results = scripted_results or [{"status": "ok"}]
        self.put_calls: list[FakePutLogsRequest] = []

    def put_logs(self, request: FakePutLogsRequest) -> Any:
        """Execute put_logs and return scripted result.

        Args:
            request: Put request.

        Returns:
            Any: Scripted success value.

        Raises:
            Exception: Scripted exception value.
        """
        self.put_calls.append(request)
        result = self.scripted_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _build_sls(
    monkeypatch: pytest.MonkeyPatch,
    client: FakeSlsClient,
) -> AliCloudSls:
    """Build AliCloudSls with faked SDK dependencies.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        client: Fake SDK client.

    Returns:
        AliCloudSls: Configured client.
    """
    monkeypatch.setattr(sls_module, "LogItem", FakeLogItem)
    monkeypatch.setattr(sls_module, "PutLogsRequest", FakePutLogsRequest)
    monkeypatch.setattr(sls_module, "SlsLogClient", lambda *_args, **_kwargs: client)
    monkeypatch.setattr(sls_module, "AUTH_VERSION_4", "v4")
    monkeypatch.setattr("pytbox.alicloud.sls.time.sleep", lambda _s: None)
    return AliCloudSls(
        access_key_id="ak-id",
        access_key_secret="secret-ak",
        project="project-a",
        logstore="logstore-a",
        timeout=1,
        max_retries=3,
        retry_backoff_base=0.1,
        idempotency_ttl_seconds=300,
    )


def test_put_logs_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """put_logs should return ReturnResponse on success."""
    client = FakeSlsClient(scripted_results=[{"ok": 1}])
    sls = _build_sls(monkeypatch=monkeypatch, client=client)

    response = sls.put_logs(
        level="INFO",
        msg="test",
        app="app",
        caller_filename="f.py",
        caller_lineno=9,
        caller_function="func",
        call_full_filename="/tmp/f.py",
    )

    assert isinstance(response, ReturnResponse)
    assert response.code == 0
    assert len(client.put_calls) == 1
    assert client.put_calls[0].topic == "program"


def test_put_logs_retries_then_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """put_logs should retry on failure until success."""
    client = FakeSlsClient(
        scripted_results=[RuntimeError("1"), RuntimeError("2"), {"ok": 1}],
    )
    sls = _build_sls(monkeypatch=monkeypatch, client=client)

    response = sls.put_logs(
        level="WARNING",
        msg="retry",
        app="app",
        caller_filename="f.py",
        caller_lineno=9,
        caller_function="func",
        call_full_filename="/tmp/f.py",
    )

    assert response.code == 0
    assert len(client.put_calls) == 3


def test_put_logs_is_idempotent_within_cache_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same payload within cache window should be written once."""
    client = FakeSlsClient(scripted_results=[{"ok": 1}])
    sls = _build_sls(monkeypatch=monkeypatch, client=client)

    first = sls.put_logs(level="INFO", msg="same", app="app")
    second = sls.put_logs(level="INFO", msg="same", app="app")

    assert first.code == 0
    assert second.code == 0
    assert len(client.put_calls) == 1


def test_put_logs_for_meraki_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """put_logs_for_meraki should return ReturnResponse on success."""
    client = FakeSlsClient(scripted_results=[{"ok": 1}])
    sls = _build_sls(monkeypatch=monkeypatch, client=client)

    response = sls.put_logs_for_meraki([("k", "v"), ("severity", "high")])

    assert response.code == 0
    assert len(client.put_calls) == 1
    assert client.put_calls[0].topic == ""


def test_put_logs_retries_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Timeout should trigger retry flow."""
    client = FakeSlsClient(scripted_results=[{"ok": 1}])
    sls = _build_sls(monkeypatch=monkeypatch, client=client)

    call_counter = {"count": 0}

    def fake_invoke(_caller: Any, *_args: Any) -> dict[str, int]:
        call_counter["count"] += 1
        if call_counter["count"] == 1:
            raise FutureTimeoutError()
        return {"ok": 1}

    monkeypatch.setattr(sls, "_invoke_with_timeout", fake_invoke)

    response = sls.put_logs(level="INFO", msg="timeout", app="app")

    assert response.code == 0
    assert call_counter["count"] == 2


def test_put_logs_logs_required_fields_without_secret(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Structured step logs should include required keys and avoid secrets."""
    client = FakeSlsClient(scripted_results=[{"ok": 1}])
    sls = _build_sls(monkeypatch=monkeypatch, client=client)
    caplog.set_level("INFO")

    response = sls.put_logs(level="INFO", msg="secret-safe", app="app")

    assert response.code == 0
    text = caplog.text
    assert "task_id=" in text
    assert "target=project-a/logstore-a" in text
    assert "duration_ms=" in text
    assert "secret-ak" not in text
