#!/usr/bin/env python3

"""Unit tests for AppLogger."""

from __future__ import annotations

from typing import Any

import pytest

from pytbox.log.logger import AppLogger


class DummyVictoria:
    """Dummy VictoriaLogs sink."""

    def __init__(self, raise_error: bool = False) -> None:
        """Initialize dummy sink.

        Args:
            raise_error: Whether to raise an exception on send.
        """
        self.raise_error = raise_error
        self.calls: list[dict[str, Any]] = []

    def send_program_log(self, **kwargs: Any) -> None:
        """Record call and optionally raise.

        Args:
            **kwargs: Call arguments.
        """
        self.calls.append(kwargs)
        if self.raise_error:
            raise RuntimeError("victorialog down")


class DummySls:
    """Dummy SLS sink."""

    def __init__(self, raise_error: bool = False) -> None:
        """Initialize dummy sink.

        Args:
            raise_error: Whether to raise an exception on put.
        """
        self.raise_error = raise_error
        self.calls: list[dict[str, Any]] = []

    def put_logs(self, **kwargs: Any) -> None:
        """Record call and optionally raise.

        Args:
            **kwargs: Call arguments.
        """
        self.calls.append(kwargs)
        if self.raise_error:
            raise RuntimeError("sls down")


class DummyCollection:
    """Dummy mongo collection for dedupe tests."""

    def __init__(self, latest_message: dict[str, Any] | None = None) -> None:
        """Initialize dummy collection.

        Args:
            latest_message: Latest stored message document.
        """
        self.latest_message = latest_message
        self.inserted_docs: list[dict[str, Any]] = []

    def find_one(self, _query: dict[str, Any], sort: list[tuple[str, int]]) -> dict[str, Any] | None:
        """Return configured latest message.

        Args:
            _query: Query fields.
            sort: Sort config.

        Returns:
            dict[str, Any] | None: Latest message document.
        """
        _ = sort
        return self.latest_message

    def insert_one(self, doc: dict[str, Any]) -> None:
        """Save inserted document for assertions.

        Args:
            doc: Document to insert.
        """
        self.inserted_docs.append(doc)


class DummyMongo:
    """Dummy mongo wrapper."""

    def __init__(self, collection: DummyCollection) -> None:
        """Initialize wrapper.

        Args:
            collection: Collection instance.
        """
        self.collection = collection


class DummyFeishuExtensions:
    """Dummy Feishu extension methods."""

    def __init__(self) -> None:
        """Initialize extension stub."""
        self.notifications: list[dict[str, Any]] = []

    def send_message_notify(self, title: str, content: str) -> None:
        """Record sent notification.

        Args:
            title: Notification title.
            content: Notification body.
        """
        self.notifications.append({"title": title, "content": content})

    def format_rich_text(self, text: str, color: str, bold: bool) -> str:
        """Return deterministic rich text placeholder.

        Args:
            text: Raw text.
            color: Text color.
            bold: Whether bold style is enabled.

        Returns:
            str: Formatted placeholder.
        """
        return f"{text}-{color}-{bold}"


class DummyFeishu:
    """Dummy Feishu client."""

    def __init__(self) -> None:
        """Initialize Feishu dummy."""
        self.extensions = DummyFeishuExtensions()


class DummyDida:
    """Dummy Dida client."""

    def __init__(self) -> None:
        """Initialize Dida dummy."""
        self.tasks: list[dict[str, Any]] = []

    def task_create(self, **kwargs: Any) -> None:
        """Record created task.

        Args:
            **kwargs: Task payload.
        """
        self.tasks.append(kwargs)


def _build_logger(monkeypatch: pytest.MonkeyPatch, **kwargs: Any) -> AppLogger:
    """Build logger with deterministic caller info.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        **kwargs: AppLogger kwargs.

    Returns:
        AppLogger: Configured logger.
    """
    app_logger = AppLogger(app_name="tests.logger", **kwargs)
    monkeypatch.setattr(
        app_logger,
        "_get_caller_info",
        lambda: ("fake.py", 123, "test_func", "/tmp/fake.py"),
    )
    return app_logger


def test_logger_levels_isolate_external_sink_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """All level methods should not raise when sinks fail."""
    app_logger = _build_logger(
        monkeypatch=monkeypatch,
        enable_victorialog=True,
        enable_sls=True,
    )
    app_logger.victorialog = DummyVictoria(raise_error=True)
    app_logger.sls = DummySls(raise_error=True)

    app_logger.debug("debug")
    app_logger.info("info")
    app_logger.warning("warning")
    app_logger.error("error")
    app_logger.critical("critical")
    app_logger.exception("exception")

    assert len(app_logger.victorialog.calls) == 6
    assert len(app_logger.sls.calls) == 6


def test_logger_info_feishu_notify_without_client_does_not_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Feishu notify option should be safe when Feishu client is missing."""
    app_logger = _build_logger(monkeypatch=monkeypatch)
    app_logger.info("notify", feishu_notify=True)


def test_logger_error_dedupe_within_36_hours_skips_notifications(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Error alerts should be deduped within 36 hours."""
    collection = DummyCollection(latest_message={"time": "old"})
    feishu = DummyFeishu()
    dida = DummyDida()
    app_logger = _build_logger(
        monkeypatch=monkeypatch,
        mongo=DummyMongo(collection),
        feishu=feishu,
        dida=dida,
    )

    monkeypatch.setattr("pytbox.log.logger.TimeUtils.get_now_time_mongo", lambda: "now")
    monkeypatch.setattr("pytbox.log.logger.TimeUtils.get_time_diff_hours", lambda _a, _b: 12)

    app_logger.error("same-message")

    assert collection.inserted_docs == []
    assert feishu.extensions.notifications == []
    assert dida.tasks == []


def test_logger_error_sends_notifications_when_dedupe_window_expired(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Error alerts should notify when latest duplicate is older than 36 hours."""
    collection = DummyCollection(latest_message={"time": "old"})
    feishu = DummyFeishu()
    dida = DummyDida()
    app_logger = _build_logger(
        monkeypatch=monkeypatch,
        mongo=DummyMongo(collection),
        feishu=feishu,
        dida=dida,
    )

    monkeypatch.setattr("pytbox.log.logger.TimeUtils.get_now_time_mongo", lambda: "now")
    monkeypatch.setattr("pytbox.log.logger.TimeUtils.get_time_diff_hours", lambda _a, _b: 40)

    app_logger.error("same-message")

    assert len(collection.inserted_docs) == 1
    assert len(feishu.extensions.notifications) == 1
    assert len(dida.tasks) == 1


def test_logger_error_with_feishu_and_missing_mongo_is_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Error path should not raise when mongo client is missing."""
    app_logger = _build_logger(
        monkeypatch=monkeypatch,
        feishu=DummyFeishu(),
        mongo=None,
    )
    app_logger.error("no-mongo")
