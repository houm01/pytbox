#!/usr/bin/env python3

"""Unit tests for AlertHandler delivery contract and failure behavior."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any, Optional

import pytest

from pytbox.alert.alert_handler import AlertDeliveryError, AlertHandler
from pytbox.schemas.codes import RespCode
from pytbox.schemas.response import ReturnResponse


@dataclass
class _DummyInsertResult:
    inserted_id: str = "mongo-1"


@dataclass
class _DummyUpdateResult:
    matched_count: int = 1
    modified_count: int = 1


class DummyCollection:
    """Dummy mongo collection."""

    def __init__(self) -> None:
        """Initialize dummy collection state."""
        self.raise_on_insert: Optional[Exception] = None
        self.raise_on_find: Optional[Exception] = None
        self.inserted_docs: list[dict[str, Any]] = []
        self.update_calls: list[tuple[dict[str, Any], dict[str, Any]]] = []
        self.find_alarm_doc: dict[str, Any] | None = {
            "event_time": datetime.datetime(2026, 2, 1, 8, 0, tzinfo=datetime.timezone.utc),
            "dida_task_id": "task-1",
        }

    def insert_one(self, document: dict[str, Any]) -> _DummyInsertResult:
        """Insert one document."""
        if self.raise_on_insert:
            raise self.raise_on_insert
        self.inserted_docs.append(document)
        return _DummyInsertResult()

    def update_one(
        self,
        filter_doc: dict[str, Any],
        update_doc: dict[str, Any],
    ) -> _DummyUpdateResult:
        """Update one document."""
        self.update_calls.append((filter_doc, update_doc))
        return _DummyUpdateResult()

    def find_one(
        self,
        _filter_doc: dict[str, Any],
        _projection: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Return preconfigured document."""
        if self.raise_on_find:
            raise self.raise_on_find
        return self.find_alarm_doc


class DummyMongo:
    """Dummy mongo wrapper used by AlertHandler."""

    def __init__(self, alarm_exists: bool = True) -> None:
        """Initialize dummy mongo.

        Args:
            alarm_exists: Whether dedupe check should pass.
        """
        self.alarm_exists = alarm_exists
        self.collection = DummyCollection()

    def check_alarm_exist(self, event_type: str, event_content: str) -> bool:
        """Return configured dedupe decision."""
        _ = (event_type, event_content)
        return self.alarm_exists

    def recent_alerts(self, event_content: str) -> str:
        """Return deterministic history string."""
        _ = event_content
        return "历史告警样例"


class DummyFeishuExtensions:
    """Dummy Feishu extensions endpoint."""

    def __init__(self, response: Any = None, raise_error: Exception | None = None) -> None:
        """Initialize dummy feishu extension."""
        self.response = response
        self.raise_error = raise_error
        self.calls: list[dict[str, Any]] = []

    def send_alert_notify(self, **kwargs: Any) -> Any:
        """Record call and return configured response."""
        self.calls.append(kwargs)
        if self.raise_error:
            raise self.raise_error
        if self.response is None:
            return ReturnResponse.ok(data={"message_id": "msg-1"})
        return self.response


class DummyFeishu:
    """Dummy Feishu client."""

    def __init__(self, response: Any = None, raise_error: Exception | None = None) -> None:
        """Initialize dummy feishu client."""
        self.extensions = DummyFeishuExtensions(response=response, raise_error=raise_error)


class DummyDida:
    """Dummy Dida client."""

    def __init__(
        self,
        create_response: Any = None,
        update_response: Any = None,
        complete_response: Any = None,
        raise_on_create: Exception | None = None,
    ) -> None:
        """Initialize dummy dida client."""
        self.create_response = create_response or ReturnResponse.ok(data={"id": "task-1"})
        self.update_response = update_response or ReturnResponse.ok(data={"ok": True})
        self.complete_response = complete_response or ReturnResponse.ok(data={"ok": True})
        self.raise_on_create = raise_on_create
        self.create_calls: list[dict[str, Any]] = []

    def task_create(self, **kwargs: Any) -> Any:
        """Create one task."""
        self.create_calls.append(kwargs)
        if self.raise_on_create:
            raise self.raise_on_create
        return self.create_response

    def task_update(self, **_kwargs: Any) -> Any:
        """Update one task."""
        return self.update_response

    def task_complete(self, **_kwargs: Any) -> Any:
        """Complete one task."""
        return self.complete_response


class DummyMail:
    """Dummy mail client."""

    def __init__(self, send_result: bool = True, raise_error: Exception | None = None) -> None:
        """Initialize dummy mail client."""
        self.send_result = send_result
        self.raise_error = raise_error
        self.calls: list[dict[str, Any]] = []

    def send_mail(self, **kwargs: Any) -> bool:
        """Send one mail and return configured result."""
        self.calls.append(kwargs)
        if self.raise_error:
            raise self.raise_error
        return self.send_result


@pytest.fixture
def now_time(monkeypatch: pytest.MonkeyPatch) -> datetime.datetime:
    """Freeze alert time for deterministic assertions."""
    now = datetime.datetime(2026, 2, 1, 8, 30, tzinfo=datetime.timezone.utc)
    monkeypatch.setattr("pytbox.alert.alert_handler.TimeUtils.get_now_time_mongo", lambda: now)
    return now


def test_send_alert_trigger_mongo_only_success(now_time: datetime.datetime) -> None:
    """Trigger event should persist to mongo and return detailed success response."""
    _ = now_time
    mongo = DummyMongo(alarm_exists=True)
    handler = AlertHandler(config={}, mongo_client=mongo)

    response = handler.send_alert(
        event_type="trigger",
        event_name="CPU high",
        event_content="cpu > 90%",
        entity_name="node-1",
    )

    assert isinstance(response, ReturnResponse)
    assert response.code == int(RespCode.OK)
    payload = response.data
    assert payload["failed_channels"] == []
    assert payload["channels"]["mongo"]["ok"] is True
    assert payload["channels"]["mongo"]["data"]["inserted_id"] == "mongo-1"


def test_send_alert_duplicate_trigger_returns_no_data(now_time: datetime.datetime) -> None:
    """Duplicate unresolved trigger should be skipped as no-data response."""
    _ = now_time
    mongo = DummyMongo(alarm_exists=False)
    handler = AlertHandler(config={}, mongo_client=mongo)

    response = handler.send_alert(
        event_type="trigger",
        event_name="CPU high",
        event_content="cpu > 90%",
        entity_name="node-1",
    )

    assert response.code == int(RespCode.NO_DATA)
    assert response.data["skipped"] is True
    assert response.data["reason"] == "duplicate unresolved alert skipped"


def test_send_alert_resolved_requires_mongo_id(now_time: datetime.datetime) -> None:
    """Resolved event must provide mongo id."""
    _ = now_time
    handler = AlertHandler(config={}, mongo_client=DummyMongo())

    with pytest.raises(ValueError, match="mongo_id"):
        handler.send_alert(
            event_type="resolved",
            event_name="CPU high",
            event_content="cpu > 90%",
            entity_name="node-1",
            mongo_id=None,
        )


def test_send_alert_feishu_non_zero_response_raises(now_time: datetime.datetime) -> None:
    """Feishu non-zero return code should fail aggregated delivery."""
    _ = now_time
    feishu = DummyFeishu(response=ReturnResponse(code=1001, msg="feishu failed", data={"x": 1}))
    handler = AlertHandler(
        config={"feishu": {"enable_alert": True, "receive_id": "ou_x"}},
        mongo_client=DummyMongo(),
        feishu_client=feishu,
    )

    with pytest.raises(AlertDeliveryError) as exc:
        handler.send_alert(
            event_type="trigger",
            event_name="CPU high",
            event_content="cpu > 90%",
            entity_name="node-1",
        )

    payload = exc.value.response.data
    assert "feishu" in payload["failed_channels"]
    assert payload["channels"]["feishu"]["ok"] is False


def test_send_alert_feishu_exception_raises(now_time: datetime.datetime) -> None:
    """Feishu exceptions should be aggregated then raised."""
    _ = now_time
    handler = AlertHandler(
        config={"feishu": {"enable_alert": True, "receive_id": "ou_x"}},
        mongo_client=DummyMongo(),
        feishu_client=DummyFeishu(raise_error=RuntimeError("feishu timeout")),
    )

    with pytest.raises(AlertDeliveryError) as exc:
        handler.send_alert(
            event_type="trigger",
            event_name="CPU high",
            event_content="cpu > 90%",
            entity_name="node-1",
        )

    assert "feishu" in exc.value.response.data["failed_channels"]


def test_send_alert_dida_non_zero_response_raises(now_time: datetime.datetime) -> None:
    """Dida non-zero return code should fail aggregated delivery."""
    _ = now_time
    dida = DummyDida(create_response=ReturnResponse(code=1002, msg="dida failed", data={}))
    handler = AlertHandler(
        config={"dida": {"enable_alert": True, "alert_project_id": "p1"}},
        mongo_client=DummyMongo(),
        dida_client=dida,
    )

    with pytest.raises(AlertDeliveryError) as exc:
        handler.send_alert(
            event_type="trigger",
            event_name="CPU high",
            event_content="cpu > 90%",
            entity_name="node-1",
        )

    assert "dida" in exc.value.response.data["failed_channels"]


def test_send_alert_mail_false_raises(now_time: datetime.datetime) -> None:
    """Mail returning False should be treated as failure."""
    _ = now_time
    handler = AlertHandler(
        config={
            "mail": {
                "enable_mail": True,
                "mail_address": "a@example.com",
                "subject_trigger": "trigger",
                "subject_resolved": "resolved",
            }
        },
        mongo_client=DummyMongo(),
        mail_client=DummyMail(send_result=False),
    )

    with pytest.raises(AlertDeliveryError) as exc:
        handler.send_alert(
            event_type="trigger",
            event_name="CPU high",
            event_content="cpu > 90%",
            entity_name="node-1",
        )

    assert "mail" in exc.value.response.data["failed_channels"]


def test_send_alert_mongo_insert_failure_raises(now_time: datetime.datetime) -> None:
    """Mongo insert failures should still produce detailed aggregated error."""
    _ = now_time
    mongo = DummyMongo()
    mongo.collection.raise_on_insert = RuntimeError("mongo down")
    handler = AlertHandler(config={}, mongo_client=mongo)

    with pytest.raises(AlertDeliveryError) as exc:
        handler.send_alert(
            event_type="trigger",
            event_name="CPU high",
            event_content="cpu > 90%",
            entity_name="node-1",
        )

    payload = exc.value.response.data
    assert payload["failed_channels"] == ["mongo"]
    assert payload["channels"]["mongo"]["ok"] is False


def test_send_alert_enabled_channel_without_client_raises(now_time: datetime.datetime) -> None:
    """Enabled optional channel must have matching client instance."""
    _ = now_time
    handler = AlertHandler(
        config={"feishu": {"enable_alert": True, "receive_id": "ou_x"}},
        mongo_client=DummyMongo(),
        feishu_client=None,
    )

    with pytest.raises(ValueError, match="feishu client is required"):
        handler.send_alert(
            event_type="trigger",
            event_name="CPU high",
            event_content="cpu > 90%",
            entity_name="node-1",
        )


def test_send_alert_success_payload_contains_channel_schema(now_time: datetime.datetime) -> None:
    """Success response should include full per-channel schema."""
    _ = now_time
    mongo = DummyMongo()
    feishu = DummyFeishu()
    dida = DummyDida()
    mail = DummyMail(send_result=True)
    handler = AlertHandler(
        config={
            "feishu": {"enable_alert": True, "receive_id": "ou_x"},
            "dida": {"enable_alert": True, "alert_project_id": "p1"},
            "mail": {
                "enable_mail": True,
                "mail_address": "a@example.com",
                "subject_trigger": "trigger",
                "subject_resolved": "resolved",
            },
            "wecom": {"enable": False},
        },
        mongo_client=mongo,
        feishu_client=feishu,
        dida_client=dida,
        mail_client=mail,
    )

    response = handler.send_alert(
        event_type="trigger",
        event_name="CPU high",
        event_content="cpu > 90%",
        entity_name="node-1",
        priority="critical",
    )

    assert response.code == int(RespCode.OK)
    payload = response.data
    channels = payload["channels"]
    assert payload["failed_channels"] == []

    for channel_name in ["mongo", "feishu", "dida", "mail", "wecom"]:
        assert set(channels[channel_name].keys()) == {
            "enabled",
            "attempted",
            "ok",
            "action",
            "error",
            "data",
        }

    assert channels["feishu"]["ok"] is True
    assert channels["dida"]["ok"] is True
    assert channels["mail"]["ok"] is True
