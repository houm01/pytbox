#!/usr/bin/env python3

"""Contract tests for volc cloud module."""

from __future__ import annotations

from concurrent.futures import TimeoutError as FutureTimeoutError
from contextlib import contextmanager
import importlib
import json
import sys
import types
from typing import Any

import pytest

from pytbox.schemas.response import ReturnResponse


def _install_fake_volc_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install fake volc SDK modules into ``sys.modules``."""

    def register(name: str, module: types.ModuleType) -> None:
        monkeypatch.setitem(sys.modules, name, module)

    core_mod = types.ModuleType("volcenginesdkcore")

    class Configuration:
        """Fake SDK configuration."""

        def __init__(self) -> None:
            self.ak = ""
            self.sk = ""
            self.region = ""

    class ApiClient:
        """Fake SDK ApiClient."""

        def __init__(self, configuration: Configuration) -> None:
            self.configuration = configuration

    core_mod.Configuration = Configuration
    core_mod.ApiClient = ApiClient
    register("volcenginesdkcore", core_mod)

    ecs_mod = types.ModuleType("volcenginesdkecs")

    class DescribeInstancesRequest:
        """Fake request."""

        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    class ECSApi:
        """Fake ECS API."""

        def __init__(self, _api_client: Any) -> None:
            self.response_payload = {"instances": []}

        def describe_instances(self, _request: Any) -> Any:
            return types.SimpleNamespace(to_dict=lambda: self.response_payload)

    ecs_mod.DescribeInstancesRequest = DescribeInstancesRequest
    ecs_mod.ECSApi = ECSApi
    register("volcenginesdkecs", ecs_mod)

    volcobserve_pkg = types.ModuleType("volcenginesdkvolcobserve")

    class VOLCOBSERVEApi:
        """Fake VolcObserve API."""

        def __init__(self, _api_client: Any) -> None:
            self.response_payload = {"data": []}

        def get_metric_data(self, _request: Any) -> Any:
            return types.SimpleNamespace(to_dict=lambda: self.response_payload)

    volcobserve_pkg.VOLCOBSERVEApi = VOLCOBSERVEApi
    register("volcenginesdkvolcobserve", volcobserve_pkg)

    models_pkg = types.ModuleType("volcenginesdkvolcobserve.models")
    register("volcenginesdkvolcobserve.models", models_pkg)

    dim_mod = types.ModuleType("volcenginesdkvolcobserve.models.dimension_for_get_metric_data_input")
    inst_mod = types.ModuleType("volcenginesdkvolcobserve.models.instance_for_get_metric_data_input")
    req_mod = types.ModuleType("volcenginesdkvolcobserve.models.get_metric_data_request")

    class DimensionForGetMetricDataInput:
        """Fake dimension model."""

        def __init__(self, name: str, value: str) -> None:
            self.name = name
            self.value = value

    class InstanceForGetMetricDataInput:
        """Fake instance model."""

        def __init__(self, dimensions: list[Any]) -> None:
            self.dimensions = dimensions

    class GetMetricDataRequest:
        """Fake request model."""

        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    dim_mod.DimensionForGetMetricDataInput = DimensionForGetMetricDataInput
    inst_mod.InstanceForGetMetricDataInput = InstanceForGetMetricDataInput
    req_mod.GetMetricDataRequest = GetMetricDataRequest
    register("volcenginesdkvolcobserve.models.dimension_for_get_metric_data_input", dim_mod)
    register("volcenginesdkvolcobserve.models.instance_for_get_metric_data_input", inst_mod)
    register("volcenginesdkvolcobserve.models.get_metric_data_request", req_mod)


def _load_volc_modules() -> tuple[Any, Any, Any, Any]:
    """Load and reload volc target modules."""
    errors_mod = importlib.reload(importlib.import_module("pytbox.cloud.volc.errors"))
    client_mod = importlib.reload(importlib.import_module("pytbox.cloud.volc.client"))
    ecs_mod = importlib.reload(importlib.import_module("pytbox.cloud.volc.ecs"))
    cloudmonitor_mod = importlib.reload(importlib.import_module("pytbox.cloud.volc.cloudmonitor"))
    _volc_mod = importlib.reload(importlib.import_module("pytbox.cloud.volc.volc"))
    return errors_mod, client_mod, ecs_mod, cloudmonitor_mod


def test_map_volc_exception_parses_body_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Error mapping should parse body json and classify invalid params."""
    _install_fake_volc_sdk(monkeypatch)
    errors_mod, _client_mod, _ecs_mod, _cloudmonitor_mod = _load_volc_modules()

    err_body = json.dumps(
        {
            "ResponseMetadata": {
                "Error": {
                    "Code": "InvalidParameter",
                    "Message": "invalid parameter foo",
                }
            }
        }
    )
    error = RuntimeError("bad request")
    setattr(error, "body", err_body)

    mapped = errors_mod.map_volc_exception("ecs_list", error)
    assert isinstance(mapped, errors_mod.InvalidRequest)
    assert "invalid params" in str(mapped)


def test_volc_client_call_retries_on_timeout(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """Volc client call should retry timeout and produce key-step logs."""
    _install_fake_volc_sdk(monkeypatch)
    _errors_mod, client_mod, _ecs_mod, _cloudmonitor_mod = _load_volc_modules()

    cfg = client_mod.VolcConfig(region="cn-shanghai", timeout_s=8.0, retries=2, retry_backoff_s=0.5)
    client = client_mod.VolcClient(creds=client_mod.VolcCreds(ak="ak", sk="secret-sk"), cfg=cfg)

    counter = {"count": 0}

    def fake_invoke(_caller: Any) -> dict[str, int]:
        counter["count"] += 1
        if counter["count"] < 3:
            raise FutureTimeoutError()
        return {"ok": 1}

    sleep_calls: list[float] = []
    monkeypatch.setattr(client, "_invoke_with_timeout", fake_invoke)
    monkeypatch.setattr("pytbox.cloud.volc.client.time.sleep", lambda sec: sleep_calls.append(sec))

    caplog.set_level("INFO")
    result = client.call("ecs_list", lambda: {"ok": 1})

    assert result == {"ok": 1}
    assert counter["count"] == 3
    assert sleep_calls == [0.5, 1.0]
    assert "task_id=" in caplog.text
    assert "target=volc:ecs_list" in caplog.text
    assert "secret-sk" not in caplog.text


def test_volc_client_use_region_restores_previous_region(monkeypatch: pytest.MonkeyPatch) -> None:
    """Temporary region context should restore previous value."""
    _install_fake_volc_sdk(monkeypatch)
    _errors_mod, client_mod, _ecs_mod, _cloudmonitor_mod = _load_volc_modules()

    client = client_mod.VolcClient(
        creds=client_mod.VolcCreds(ak="ak", sk="sk"),
        cfg=client_mod.VolcConfig(region="cn-shanghai"),
    )
    assert client.api_client.configuration.region == "cn-shanghai"

    with client.use_region("cn-beijing"):
        assert client.api_client.configuration.region == "cn-beijing"
    assert client.api_client.configuration.region == "cn-shanghai"


def test_volc_ecs_get_instance_and_list_instance_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """ECS helper APIs should return single instance and id list."""
    _install_fake_volc_sdk(monkeypatch)
    _errors_mod, _client_mod, ecs_mod, _cloudmonitor_mod = _load_volc_modules()

    class FakeApi:
        """Fake ECS API."""

        def describe_instances(self, _request: Any) -> Any:
            return types.SimpleNamespace(
                to_dict=lambda: {
                    "instances": [
                        {"instance_id": "i-1", "name": "first"},
                        {"instance_id": "i-2", "name": "second"},
                    ]
                }
            )

    class FakeClient:
        """Fake Volc client."""

        def __init__(self) -> None:
            self.cfg = types.SimpleNamespace(region="cn-shanghai")
            self._region = "cn-shanghai"
            self.api = FakeApi()

        @contextmanager
        def use_region(self, region: str | None) -> Any:
            previous = self._region
            self._region = region or self.cfg.region
            try:
                yield
            finally:
                self._region = previous

        def ecs_api(self) -> Any:
            return self.api

        def call(self, _action: str, caller: Any) -> Any:
            return caller()

    resource = ecs_mod.ECSResource(FakeClient())
    instance_resp = resource.get_instance("i-1")
    ids_resp = resource.list_instance_ids()

    assert isinstance(instance_resp, ReturnResponse)
    assert instance_resp.data["instance_id"] == "i-1"
    assert ids_resp.data == ["i-1", "i-2"]


def test_volc_cloudmonitor_get_metric_data_and_latest_point(monkeypatch: pytest.MonkeyPatch) -> None:
    """CloudMonitor should always return ReturnResponse and parse latest point."""
    _install_fake_volc_sdk(monkeypatch)
    _errors_mod, _client_mod, _ecs_mod, cloudmonitor_mod = _load_volc_modules()

    class FakeObserveApi:
        """Fake VolcObserve API."""

        def __init__(self) -> None:
            self.raise_error = False

        def get_metric_data(self, _request: Any) -> Any:
            if self.raise_error:
                raise RuntimeError("boom")
            return types.SimpleNamespace(
                to_dict=lambda: {
                    "data": {
                        "metric_data_results": [
                            {
                                "datapoints": [
                                    {"timestamp": 1700000000000, "value": 11},
                                    {"timestamp": 1700000002000, "value": "12.5"},
                                ]
                            }
                        ]
                    }
                }
            )

    class FakeClient:
        """Fake Volc client."""

        def __init__(self) -> None:
            self.observe = FakeObserveApi()
            self.cfg = types.SimpleNamespace(region="cn-shanghai")
            self.current_region = "cn-shanghai"

        @contextmanager
        def use_region(self, region: str | None) -> Any:
            previous = self.current_region
            self.current_region = region or self.cfg.region
            try:
                yield
            finally:
                self.current_region = previous

        def volc_observe_api(self) -> Any:
            return self.observe

        def call(self, _action: str, caller: Any) -> Any:
            return caller()

    fake_client = FakeClient()
    resource = cloudmonitor_mod.CloudMonitorResource(fake_client)

    metric_resp = resource.get_metric_data(
        namespace="VCM_ECS",
        sub_namespace="Instance",
        metric_name="CpuTotal",
        dimensions={"ResourceID": "i-1"},
        last_minute=5,
    )
    latest_resp = resource.latest_metric_point(
        namespace="VCM_ECS",
        sub_namespace="Instance",
        metric_name="CpuTotal",
        dimensions={"ResourceID": "i-1"},
        last_minute=5,
    )
    assert isinstance(metric_resp, ReturnResponse)
    assert metric_resp.code == 0
    assert isinstance(latest_resp, ReturnResponse)
    assert latest_resp.data == {"ts": 1700000002, "value": 12.5}

    fake_client.observe.raise_error = True
    failed_resp = resource.get_metric_data(
        namespace="VCM_ECS",
        sub_namespace="Instance",
        metric_name="CpuTotal",
        dimensions={"ResourceID": "i-1"},
        last_minute=5,
    )
    assert isinstance(failed_resp, ReturnResponse)
    assert failed_resp.code == 1
