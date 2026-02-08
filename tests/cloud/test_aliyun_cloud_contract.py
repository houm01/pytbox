#!/usr/bin/env python3

"""Contract tests for aliyun cloud module."""

from __future__ import annotations

from concurrent.futures import TimeoutError as FutureTimeoutError
import importlib
import json
import sys
import types
from typing import Any

import pytest

from pytbox.schemas.response import ReturnResponse


def _install_fake_aliyun_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install fake aliyun SDK modules into ``sys.modules``."""

    def register(name: str, module: types.ModuleType) -> None:
        monkeypatch.setitem(sys.modules, name, module)

    tea_pkg = types.ModuleType("Tea")
    tea_exc_mod = types.ModuleType("Tea.exceptions")

    class TeaException(Exception):
        """Fake TeaException."""

        def __init__(self, message: str = "", code: str | None = None) -> None:
            super().__init__(message)
            self.message = message
            self.code = code

    class UnretryableException(Exception):
        """Fake UnretryableException."""

    tea_exc_mod.TeaException = TeaException
    tea_exc_mod.UnretryableException = UnretryableException
    register("Tea", tea_pkg)
    register("Tea.exceptions", tea_exc_mod)

    openapi_pkg = types.ModuleType("alibabacloud_tea_openapi")
    openapi_models_mod = types.ModuleType("alibabacloud_tea_openapi.models")

    class OpenApiConfig:
        """Fake OpenAPI config."""

        def __init__(self, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)
            self.endpoint = None

    openapi_models_mod.Config = OpenApiConfig
    openapi_pkg.models = openapi_models_mod
    register("alibabacloud_tea_openapi", openapi_pkg)
    register("alibabacloud_tea_openapi.models", openapi_models_mod)

    ecs_pkg = types.ModuleType("alibabacloud_ecs20140526")
    ecs_client_mod = types.ModuleType("alibabacloud_ecs20140526.client")
    ecs_models_mod = types.ModuleType("alibabacloud_ecs20140526.models")

    class FakeEcsClient:
        """Fake ECS SDK client."""

        def __init__(self, config: Any) -> None:
            self.config = config

    class DescribeInstancesRequest:
        """Fake request."""

        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    ecs_client_mod.Client = FakeEcsClient
    ecs_models_mod.DescribeInstancesRequest = DescribeInstancesRequest
    register("alibabacloud_ecs20140526", ecs_pkg)
    register("alibabacloud_ecs20140526.client", ecs_client_mod)
    register("alibabacloud_ecs20140526.models", ecs_models_mod)

    cms_pkg = types.ModuleType("alibabacloud_cms20190101")
    cms_client_mod = types.ModuleType("alibabacloud_cms20190101.client")
    cms_models_mod = types.ModuleType("alibabacloud_cms20190101.models")

    class FakeCmsClient:
        """Fake CMS SDK client."""

        def __init__(self, config: Any) -> None:
            self.config = config

    class DescribeMetricLastRequest:
        """Fake request."""

        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    class DescribeMetricListRequest:
        """Fake request."""

        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    cms_client_mod.Client = FakeCmsClient
    cms_models_mod.DescribeMetricLastRequest = DescribeMetricLastRequest
    cms_models_mod.DescribeMetricListRequest = DescribeMetricListRequest
    cms_pkg.models = cms_models_mod
    register("alibabacloud_cms20190101", cms_pkg)
    register("alibabacloud_cms20190101.client", cms_client_mod)
    register("alibabacloud_cms20190101.models", cms_models_mod)

    ram_pkg = types.ModuleType("alibabacloud_ram20150501")
    ram_client_mod = types.ModuleType("alibabacloud_ram20150501.client")
    ram_models_mod = types.ModuleType("alibabacloud_ram20150501.models")

    class FakeRamClient:
        """Fake RAM SDK client."""

        def __init__(self, config: Any) -> None:
            self.config = config

    class _Request:
        """Generic fake request."""

        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    ram_client_mod.Client = FakeRamClient
    ram_models_mod.ListUsersRequest = _Request
    ram_models_mod.ListAccessKeysRequest = _Request
    ram_models_mod.GetAccessKeyLastUsedRequest = _Request
    ram_models_mod.GetUserMFAInfoRequest = _Request
    ram_models_mod.GetUserRequest = _Request
    ram_models_mod.ListPoliciesForUserRequest = _Request
    ram_pkg.models = ram_models_mod
    register("alibabacloud_ram20150501", ram_pkg)
    register("alibabacloud_ram20150501.client", ram_client_mod)
    register("alibabacloud_ram20150501.models", ram_models_mod)

    util_pkg = types.ModuleType("alibabacloud_tea_util")
    util_models_mod = types.ModuleType("alibabacloud_tea_util.models")

    class RuntimeOptions:
        """Fake runtime options."""

        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    util_models_mod.RuntimeOptions = RuntimeOptions
    util_pkg.models = util_models_mod
    register("alibabacloud_tea_util", util_pkg)
    register("alibabacloud_tea_util.models", util_models_mod)


def _load_aliyun_modules() -> tuple[Any, Any, Any, Any]:
    """Load and reload aliyun target modules."""
    client_mod = importlib.reload(importlib.import_module("pytbox.cloud.aliyun.client"))
    ecs_mod = importlib.reload(importlib.import_module("pytbox.cloud.aliyun.ecs"))
    cms_mod = importlib.reload(importlib.import_module("pytbox.cloud.aliyun.cms"))
    ram_mod = importlib.reload(importlib.import_module("pytbox.cloud.aliyun.ram"))
    aliyun_mod = importlib.reload(importlib.import_module("pytbox.cloud.aliyun.aliyun"))
    return client_mod, ecs_mod, cms_mod, ram_mod, aliyun_mod


def test_aliyun_options_passthrough_and_retry_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aliyun options should be passed through with retry cap."""
    _install_fake_aliyun_sdk(monkeypatch)
    _client_mod, _ecs_mod, _cms_mod, _ram_mod, aliyun_mod = _load_aliyun_modules()

    options = aliyun_mod.AliyunOptions(
        retries=99,
        cms_endpoint="custom.cms.endpoint",
        ram_endpoint="custom.ram.endpoint",
    )
    ali = aliyun_mod.Aliyun(ak="ak", sk="secret-sk", region="cn-shanghai", options=options)

    assert ali._client.cfg.retries == 3
    assert ali._client.cfg.cms_endpoint == "custom.cms.endpoint"
    assert ali._client.cfg.ram_endpoint == "custom.ram.endpoint"


def test_aliyun_client_call_retries_and_logs(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """Aliyun client call should retry timeout and emit key-step logs."""
    _install_fake_aliyun_sdk(monkeypatch)
    client_mod, _ecs_mod, _cms_mod, _ram_mod, _aliyun_mod = _load_aliyun_modules()

    cfg = client_mod.AliyunConfig(region="cn-shanghai", timeout_s=8.0, retries=2, retry_backoff_s=0.5)
    client = client_mod.AliyunClient(creds=client_mod.AliyunCreds(ak="ak", sk="secret-sk"), cfg=cfg)

    counter = {"count": 0}

    def fake_invoke(_caller: Any) -> dict[str, int]:
        counter["count"] += 1
        if counter["count"] < 3:
            raise FutureTimeoutError()
        return {"ok": 1}

    sleep_calls: list[float] = []
    monkeypatch.setattr(client, "_invoke_with_timeout", fake_invoke)
    monkeypatch.setattr("pytbox.cloud.aliyun.client.time.sleep", lambda sec: sleep_calls.append(sec))

    caplog.set_level("INFO")
    result = client.call("ecs_list", lambda: {"ok": 1})

    assert result == {"ok": 1}
    assert counter["count"] == 3
    assert sleep_calls == [0.5, 1.0]
    assert "task_id=" in caplog.text
    assert "target=aliyun:ecs_list" in caplog.text
    assert "secret-sk" not in caplog.text


def test_aliyun_ecs_get_instance_and_list_instance_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """ECS helper APIs should return single instance and id list."""
    _install_fake_aliyun_sdk(monkeypatch)
    _client_mod, ecs_mod, _cms_mod, _ram_mod, _aliyun_mod = _load_aliyun_modules()

    class FakeBody:
        """Fake response body."""

        def to_map(self) -> dict[str, Any]:
            return {
                "TotalCount": 2,
                "Instances": {
                    "Instance": [
                        {"InstanceId": "i-1", "Status": "Running"},
                        {"InstanceId": "i-2", "Status": "Stopped"},
                    ]
                },
            }

    class FakeResponse:
        """Fake SDK response."""

        body = FakeBody()

    class FakeEcsApi:
        """Fake ECS API."""

        def __init__(self) -> None:
            self.requests: list[Any] = []

        def describe_instances(self, request: Any) -> FakeResponse:
            self.requests.append(request)
            return FakeResponse()

    class FakeClient:
        """Fake Aliyun client."""

        def __init__(self) -> None:
            self.cfg = types.SimpleNamespace(region="cn-shanghai")
            self.ecs = FakeEcsApi()

        def call(self, _action: str, caller: Any) -> Any:
            return caller()

    resource = ecs_mod.ECSResource(FakeClient())
    instance_resp = resource.get_instance("i-1")
    ids_resp = resource.list_instance_ids()

    assert isinstance(instance_resp, ReturnResponse)
    assert instance_resp.data["InstanceId"] == "i-1"
    assert ids_resp.data == ["i-1", "i-2"]


def test_aliyun_cms_latest_metric_point(monkeypatch: pytest.MonkeyPatch) -> None:
    """Latest metric helper should return newest timestamp point."""
    _install_fake_aliyun_sdk(monkeypatch)
    _client_mod, _ecs_mod, cms_mod, _ram_mod, _aliyun_mod = _load_aliyun_modules()

    datapoints = json.dumps(
        [
            {"timestamp": 1700000000000, "Value": 10},
            {"timestamp": 1700000005000, "Value": "12.5"},
        ]
    )

    class FakeBody:
        """Fake body."""

        def __init__(self, raw: str) -> None:
            self.datapoints = raw

    class FakeResponse:
        """Fake SDK response."""

        def __init__(self, raw: str) -> None:
            self.body = FakeBody(raw)

    class FakeCmsApi:
        """Fake CMS API."""

        def describe_metric_last_with_options(self, _request: Any, runtime: Any) -> Any:
            _ = runtime
            return FakeResponse(datapoints)

    class FakeClient:
        """Fake Aliyun client."""

        def __init__(self) -> None:
            self.cms = FakeCmsApi()

        def call(self, _action: str, caller: Any) -> Any:
            return caller()

    resource = cms_mod.CMSResource(FakeClient())
    response = resource.latest_metric_point(
        namespace="acs_ecs_dashboard",
        metric_name="CPUUtilization",
        dimensions={"instanceId": "i-1"},
        last_minute=5,
    )

    assert isinstance(response, ReturnResponse)
    assert response.code == 0
    assert response.data == {"ts": 1700000005, "value": 12.5}


def test_aliyun_ram_aliases_match_get_methods(monkeypatch: pytest.MonkeyPatch) -> None:
    """RAM alias methods should match old get_* methods."""
    _install_fake_aliyun_sdk(monkeypatch)
    _client_mod, _ecs_mod, _cms_mod, ram_mod, _aliyun_mod = _load_aliyun_modules()

    class FakeBody:
        """Fake body."""

        def to_map(self) -> dict[str, Any]:
            return {
                "Users": {"User": [{"UserName": "alice"}]},
                "AccessKeys": {"AccessKey": [{"AccessKeyId": "ak1"}]},
                "Policies": {"Policy": [{"PolicyName": "AdministratorAccess"}]},
            }

    class FakeResponse:
        """Fake response."""

        body = FakeBody()

    class FakeRamApi:
        """Fake RAM API."""

        def list_users_with_options(self, _req: Any, runtime: Any) -> Any:
            _ = runtime
            return FakeResponse()

        def list_access_keys_with_options(self, _req: Any, runtime: Any) -> Any:
            _ = runtime
            return FakeResponse()

        def list_policies_for_user_with_options(self, _req: Any, runtime: Any) -> Any:
            _ = runtime
            return FakeResponse()

    class FakeClient:
        """Fake Aliyun client."""

        def __init__(self) -> None:
            self.ram = FakeRamApi()

        def call(self, _action: str, caller: Any) -> Any:
            return caller()

    resource = ram_mod.RAMResource(FakeClient())
    assert resource.list_users().data == resource.get_users().data
    assert resource.list_access_keys(username="alice").data == resource.get_access_keys(username="alice").data
    assert resource.list_policy_for_user(username="alice").data == resource.get_policy_for_user(username="alice").data
