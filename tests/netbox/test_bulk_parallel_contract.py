#!/usr/bin/env python3

"""Batch and parallel contract tests for NetBox client."""

from __future__ import annotations

import threading
import time
from typing import Any

import pytest

from pytbox.netbox.client import NetboxClient
from pytbox.schemas.response import ReturnResponse


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> NetboxClient:
    """Create test client.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        NetboxClient: Initialized client.
    """
    monkeypatch.setattr("pytbox.netbox.client.pynetbox.api", lambda *_args, **_kwargs: object())
    return NetboxClient(url="https://netbox.example.com", token="token")


def test_update_device_fields_success(
    client: NetboxClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PATCH update should call request layer with resolved device id."""
    captured_call: dict[str, Any] = {}

    monkeypatch.setattr(client, "get_tenant_id", lambda name: ReturnResponse(code=0, msg="ok", data=2))
    monkeypatch.setattr(client, "get_device_id", lambda name, tenant_id: ReturnResponse(code=0, msg="ok", data=9))

    def fake_request(
        method: str,
        api_url: str,
        params: dict[str, Any] | None = None,
        json_data: Any = None,
        data: Any = None,
    ) -> ReturnResponse:
        _ = params, data
        captured_call["method"] = method
        captured_call["api_url"] = api_url
        captured_call["json_data"] = json_data
        return ReturnResponse(code=0, msg="ok", data={"id": 9})

    monkeypatch.setattr(client, "_request_with_retry", fake_request)

    response = client.update_device_fields(
        name="device-1",
        tenant="tenant-1",
        fields={"custom_fields": {"SoftwareVersion": "1.0.1"}},
    )

    assert response.code == 0
    assert captured_call["method"] == "PATCH"
    assert captured_call["api_url"] == "/api/dcim/devices/9/"
    assert captured_call["json_data"] == {"custom_fields": {"SoftwareVersion": "1.0.1"}}


def test_update_device_fields_requires_fields(client: NetboxClient) -> None:
    """PATCH update should reject empty fields."""
    response = client.update_device_fields(name="device-1", fields={})
    assert response.code == 1
    assert "fields are required" in response.msg


def test_update_device_fields_requires_existing_device(
    client: NetboxClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PATCH update should fail when target device does not exist."""
    monkeypatch.setattr(client, "get_tenant_id", lambda name: ReturnResponse(code=0, msg="ok", data=2))
    monkeypatch.setattr(client, "get_device_id", lambda name, tenant_id: ReturnResponse(code=0, msg="ok", data=None))

    response = client.update_device_fields(
        name="device-1",
        tenant="tenant-1",
        fields={"status": "active"},
    )
    assert response.code == 1
    assert "not found" in response.msg


def test_bulk_update_device_fields_partial_failure_and_duplicate(
    client: NetboxClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Batch device updates should continue and report partial failures."""

    def fake_update_device_fields(
        name: str,
        fields: dict[str, Any],
        tenant: str | None = None,
    ) -> ReturnResponse:
        _ = fields, tenant
        if name == "bad-device":
            return ReturnResponse(code=1, msg="failed", data={"name": name})
        return ReturnResponse(code=0, msg="ok", data={"name": name})

    monkeypatch.setattr(client, "update_device_fields", fake_update_device_fields)

    response = client.bulk_update_device_fields(
        updates=[
            {"name": "ok-device", "tenant": "tenant-1", "fields": {"status": "active"}},
            {"name": "bad-device", "tenant": "tenant-1", "fields": {"status": "active"}},
            {"name": "ok-device", "tenant": "tenant-1", "fields": {"description": "dup"}},
        ],
        max_workers=5,
    )

    assert response.code == 1
    assert response.data["total"] == 3
    assert response.data["success"] == 1
    assert response.data["failed"] == 2
    assert response.data["results"][2]["msg"] == "bulk_update_device_fields duplicate item"


def test_bulk_update_device_fields_parallelism_over_50_items(
    client: NetboxClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Batch device updates should execute concurrently for large input."""
    stats = {"active": 0, "max": 0}
    lock = threading.Lock()

    def fake_update_device_fields(
        name: str,
        fields: dict[str, Any],
        tenant: str | None = None,
    ) -> ReturnResponse:
        _ = name, fields, tenant
        with lock:
            stats["active"] += 1
            stats["max"] = max(stats["max"], stats["active"])
        time.sleep(0.005)
        with lock:
            stats["active"] -= 1
        return ReturnResponse(code=0, msg="ok", data={"patched": True})

    monkeypatch.setattr(client, "update_device_fields", fake_update_device_fields)

    updates = [
        {"name": f"device-{index}", "tenant": "tenant-1", "fields": {"status": "active"}}
        for index in range(50)
    ]
    response = client.bulk_update_device_fields(updates=updates, max_workers=5)

    assert response.code == 0
    assert response.data["total"] == 50
    assert response.data["success"] == 50
    assert stats["max"] > 1


def test_bulk_add_or_update_interfaces_parallelism_over_50_items(
    client: NetboxClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Batch interface upserts should execute concurrently for large input."""
    stats = {"active": 0, "max": 0}
    lock = threading.Lock()

    def fake_add_or_update_interfaces(**_kwargs: Any) -> ReturnResponse:
        with lock:
            stats["active"] += 1
            stats["max"] = max(stats["max"], stats["active"])
        time.sleep(0.005)
        with lock:
            stats["active"] -= 1
        return ReturnResponse(code=0, msg="ok", data={"id": 1})

    monkeypatch.setattr(client, "add_or_update_interfaces", fake_add_or_update_interfaces)

    interfaces = [
        {"name": f"Gi0/{index}", "device": "device-1", "tenant": "tenant-1"}
        for index in range(50)
    ]
    response = client.bulk_add_or_update_interfaces(interfaces=interfaces, max_workers=5)

    assert response.code == 0
    assert response.data["total"] == 50
    assert response.data["success"] == 50
    assert stats["max"] > 1


def test_bulk_add_or_update_interfaces_duplicate_key(
    client: NetboxClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Batch interface upserts should mark duplicate keys as failures."""
    monkeypatch.setattr(
        client,
        "add_or_update_interfaces",
        lambda **_kwargs: ReturnResponse(code=0, msg="ok", data={"id": 1}),
    )

    response = client.bulk_add_or_update_interfaces(
        interfaces=[
            {"name": "Gi0/1", "device": "device-1", "tenant": "tenant-1"},
            {"name": "Gi0/1", "device": "device-1", "tenant": "tenant-1"},
            {"name": "Gi0/2", "device": "device-1", "tenant": "tenant-1"},
        ],
        max_workers=5,
    )

    assert response.code == 1
    assert response.data["total"] == 3
    assert response.data["success"] == 2
    assert response.data["failed"] == 1


def test_query_single_id_uses_cache(
    client: NetboxClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repeated single-id lookups should reuse cache and reduce GET calls."""
    calls: list[str] = []

    def fake_request(
        method: str,
        api_url: str,
        params: dict[str, Any] | None = None,
        json_data: Any = None,
        data: Any = None,
    ) -> ReturnResponse:
        _ = method, params, json_data, data
        calls.append(api_url)
        return ReturnResponse(code=0, msg="ok", data={"count": 1, "results": [{"id": 11}]})

    monkeypatch.setattr(client, "_request_with_retry", fake_request)

    first = client.get_site_id(name="site-1")
    second = client.get_site_id(name="site-1")

    assert first.code == 0
    assert second.code == 0
    assert first.data == 11
    assert second.data == 11
    assert calls == ["/api/dcim/sites/"]


def test_bulk_update_device_fields_logs_key_fields(
    client: NetboxClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Batch updates should emit key-step logs."""
    monkeypatch.setattr(
        client,
        "update_device_fields",
        lambda **_kwargs: ReturnResponse(code=0, msg="ok", data={"patched": True}),
    )
    caplog.set_level("INFO")

    response = client.bulk_update_device_fields(
        updates=[{"name": "device-1", "tenant": "tenant-1", "fields": {"status": "active"}}],
        max_workers=5,
    )

    assert response.code == 0
    text = caplog.text
    assert "task_id=" in text
    assert "target=bulk_update_device_fields" in text
    assert "duration_ms=" in text
