#!/usr/bin/env python3

"""Contract tests for aliyun SLS resource."""

from __future__ import annotations

import types
from typing import Any

import pytest

import pytbox.cloud.aliyun.sls as sls_module
from pytbox.cloud.aliyun.sls import SLSResource
from pytbox.schemas.response import ReturnResponse


class FakeLogItem:
    """Fake SLS log item."""

    def __init__(self) -> None:
        """Initialize fake log item."""
        self.contents: list[tuple[str, Any]] = []

    def set_contents(self, contents: list[tuple[str, Any]]) -> None:
        """Set fake item contents.

        Args:
            contents: Log contents.
        """
        self.contents = contents


class FakePutLogsRequest:
    """Fake SLS put logs request."""

    def __init__(
        self,
        project: str,
        logstore: str,
        topic: str,
        source: str,
        log_group: list[FakeLogItem],
        compress: bool = False,
    ) -> None:
        """Initialize fake put request.

        Args:
            project: Project name.
            logstore: Logstore name.
            topic: Topic name.
            source: Source field.
            log_group: Log item group.
            compress: Compression flag.
        """
        self.project = project
        self.logstore = logstore
        self.topic = topic
        self.source = source
        self.log_group = log_group
        self.compress = compress


class FakeGetLogsRequest:
    """Fake SLS get logs request."""

    def __init__(
        self,
        project: str,
        logstore: str,
        from_time: int,
        to_time: int,
        query: str,
    ) -> None:
        """Initialize fake get request.

        Args:
            project: Project name.
            logstore: Logstore name.
            from_time: Query start timestamp.
            to_time: Query end timestamp.
            query: Query expression.
        """
        self.project = project
        self.logstore = logstore
        self.from_time = from_time
        self.to_time = to_time
        self.query = query


class FakeLog:
    """Fake SLS log item payload."""

    def __init__(self, contents: dict[str, Any]) -> None:
        """Initialize fake log.

        Args:
            contents: Log content map.
        """
        self.contents = contents


class FakeGetLogsResponse:
    """Fake get logs response."""

    def __init__(self, logs: list[FakeLog]) -> None:
        """Initialize response.

        Args:
            logs: Fake logs.
        """
        self._logs = logs

    def get_logs(self) -> list[FakeLog]:
        """Return fake logs.

        Returns:
            list[FakeLog]: Fake logs.
        """
        return self._logs


class FakeSlsClient:
    """Fake SLS SDK client."""

    def __init__(self) -> None:
        """Initialize fake SLS client."""
        self.put_requests: list[FakePutLogsRequest] = []
        self.get_requests: list[FakeGetLogsRequest] = []
        self.get_logs_payload: list[FakeLog] = [FakeLog({"k": "v"})]

    def put_logs(self, request: FakePutLogsRequest) -> dict[str, int]:
        """Record put request and return fake success.

        Args:
            request: Put logs request.

        Returns:
            dict[str, int]: Fake response.
        """
        self.put_requests.append(request)
        return {"ok": 1}

    def get_logs(self, request: FakeGetLogsRequest) -> FakeGetLogsResponse:
        """Record get request and return fake logs.

        Args:
            request: Get logs request.

        Returns:
            FakeGetLogsResponse: Fake get logs response.
        """
        self.get_requests.append(request)
        return FakeGetLogsResponse(self.get_logs_payload)


class FakeAliyunClient:
    """Fake aliyun cloud client for SLS resource."""

    def __init__(self, *, sls_endpoint: str | None = None) -> None:
        """Initialize fake aliyun client.

        Args:
            sls_endpoint: Optional custom SLS endpoint.
        """
        self.cfg = types.SimpleNamespace(region="cn-shanghai", sls_endpoint=sls_endpoint)
        self.creds = types.SimpleNamespace(ak="ak-id", sk="secret-ak")
        self.actions: list[str] = []

    def call(self, action: str, caller: Any) -> Any:
        """Execute wrapped caller.

        Args:
            action: Action label.
            caller: Deferred callable.

        Returns:
            Any: Callable result.
        """
        self.actions.append(action)
        return caller()


def _build_resource(
    monkeypatch: pytest.MonkeyPatch,
    *,
    sls_endpoint: str | None = None,
) -> tuple[SLSResource, FakeSlsClient, FakeAliyunClient]:
    """Build SLS resource with fake SDK dependencies.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        sls_endpoint: Optional SLS endpoint override.

    Returns:
        tuple[SLSResource, FakeSlsClient, FakeAliyunClient]: Resource and fakes.
    """
    fake_sls_client = FakeSlsClient()

    def fake_client_constructor(
        endpoint: str,
        access_key_id: str,
        access_key_secret: str,
        auth_version: Any,
        region: str,
    ) -> FakeSlsClient:
        """Construct fake client and capture init arguments.

        Args:
            endpoint: SDK endpoint.
            access_key_id: Access key id.
            access_key_secret: Access key secret.
            auth_version: Auth version.
            region: Region id.

        Returns:
            FakeSlsClient: Shared fake client.
        """
        _ = (access_key_id, access_key_secret, auth_version, region)
        fake_sls_client.endpoint = endpoint  # type: ignore[attr-defined]
        return fake_sls_client

    monkeypatch.setattr(sls_module, "LogItem", FakeLogItem)
    monkeypatch.setattr(sls_module, "PutLogsRequest", FakePutLogsRequest)
    monkeypatch.setattr(sls_module, "GetLogsRequest", FakeGetLogsRequest)
    monkeypatch.setattr(sls_module, "SlsLogClient", fake_client_constructor)
    monkeypatch.setattr(sls_module, "AUTH_VERSION_4", "v4")

    fake_cloud_client = FakeAliyunClient(sls_endpoint=sls_endpoint)
    return SLSResource(fake_cloud_client), fake_sls_client, fake_cloud_client


def test_sls_put_logs_success_and_level_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    """put_logs should normalize WARN level and return success response."""
    resource, fake_sls_client, fake_cloud_client = _build_resource(
        monkeypatch=monkeypatch,
        sls_endpoint="custom.sls.endpoint",
    )

    response = resource.put_logs(
        project="project-a",
        logstore="logstore-a",
        level="WARN",
        msg="hello",
        app="app-a",
        caller_filename="file.py",
        caller_lineno=9,
        caller_function="func",
        call_full_filename="/tmp/file.py",
    )

    assert isinstance(response, ReturnResponse)
    assert response.code == 0
    assert fake_cloud_client.actions == ["sls_put_logs"]
    assert len(fake_sls_client.put_requests) == 1
    assert fake_sls_client.endpoint == "custom.sls.endpoint"

    request = fake_sls_client.put_requests[0]
    assert request.project == "project-a"
    assert request.logstore == "logstore-a"
    assert request.topic == "program"
    assert request.log_group[0].contents[0] == ("level", "WARNING")


def test_sls_put_logs_for_meraki_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Repeated meraki payload in one TTL window should be sent once."""
    resource, fake_sls_client, _fake_cloud_client = _build_resource(monkeypatch=monkeypatch)
    monkeypatch.setattr(sls_module.time, "time", lambda: 1_700_000_000.0)

    first = resource.put_logs_for_meraki(
        project="project-a",
        logstore="logstore-a",
        alert=[("k", "v"), ("severity", "high")],
    )
    second = resource.put_logs_for_meraki(
        project="project-a",
        logstore="logstore-a",
        alert=[("k", "v"), ("severity", "high")],
    )

    assert first.code == 0
    assert second.code == 0
    assert len(fake_sls_client.put_requests) == 1


def test_sls_put_logs_allows_optional_none_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """put_logs should sanitize optional ``None`` fields to empty strings."""
    resource, fake_sls_client, _fake_cloud_client = _build_resource(monkeypatch=monkeypatch)

    response = resource.put_logs(
        project="project-a",
        logstore="logstore-a",
        level="INFO",
    )

    assert response.code == 0
    assert len(fake_sls_client.put_requests) == 1

    contents = fake_sls_client.put_requests[0].log_group[0].contents
    content_map = {k: v for k, v in contents}
    assert content_map["app"] == ""
    assert content_map["msg"] == ""
    assert content_map["caller_filename"] == ""
    assert content_map["caller_lineno"] == ""
    assert content_map["caller_function"] == ""
    assert content_map["call_full_filename"] == ""


def test_sls_get_logs_returns_contents(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_logs should return structured contents list in ReturnResponse."""
    resource, fake_sls_client, fake_cloud_client = _build_resource(monkeypatch=monkeypatch)
    fake_sls_client.get_logs_payload = [
        FakeLog({"k": "v"}),
        FakeLog({"message": "hello"}),
    ]

    response = resource.get_logs(
        project="project-a",
        logstore="logstore-a",
        query="k:v",
        from_time=1,
        to_time=2,
    )

    assert isinstance(response, ReturnResponse)
    assert response.code == 0
    assert response.data == [{"k": "v"}, {"message": "hello"}]
    assert len(fake_sls_client.get_requests) == 1
    assert fake_cloud_client.actions == ["sls_get_logs"]


def test_sls_returns_failure_when_sdk_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing optional SLS SDK should return explicit failure response."""
    fake_cloud_client = FakeAliyunClient()
    resource = SLSResource(fake_cloud_client)

    monkeypatch.setattr(sls_module, "SlsLogClient", None)
    monkeypatch.setattr(sls_module, "LogItem", None)
    monkeypatch.setattr(sls_module, "PutLogsRequest", None)
    monkeypatch.setattr(sls_module, "GetLogsRequest", None)

    write_resp = resource.put_logs(project="project-a", logstore="logstore-a")
    read_resp = resource.get_logs(
        project="project-a",
        logstore="logstore-a",
        query="*",
        from_time=1,
        to_time=2,
    )

    assert write_resp.code == 1
    assert read_resp.code == 1
    assert "aliyun-log-python-sdk is required" in write_resp.msg
    assert "aliyun-log-python-sdk is required" in read_resp.msg
