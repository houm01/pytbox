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

    class DescribeEipAddressesRequest:
        """Fake request."""

        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    class DescribeDisksRequest:
        """Fake request."""

        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    class _EcsRequest:
        """Generic fake ECS request."""

        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    ecs_client_mod.Client = FakeEcsClient
    ecs_models_mod.DescribeInstancesRequest = DescribeInstancesRequest
    ecs_models_mod.DescribeEipAddressesRequest = DescribeEipAddressesRequest
    ecs_models_mod.DescribeDisksRequest = DescribeDisksRequest
    ecs_models_mod.DescribeSnapshotsRequest = _EcsRequest
    ecs_models_mod.DescribeAutoSnapshotPolicyExRequest = _EcsRequest
    ecs_models_mod.DescribeAutoSnapshotPolicyAssociationsRequest = _EcsRequest
    ecs_models_mod.DescribeSecurityGroupsRequest = _EcsRequest
    ecs_models_mod.DescribeSecurityGroupAttributeRequest = _EcsRequest
    ecs_models_mod.DescribeNetworkInterfacesRequest = _EcsRequest
    ecs_models_mod.DescribeInstancesFullStatusRequest = _EcsRequest
    ecs_models_mod.DescribeInstanceHistoryEventsRequest = _EcsRequest
    ecs_models_mod.DescribeCloudAssistantStatusRequest = _EcsRequest
    ecs_models_mod.DescribeImagesRequest = _EcsRequest
    ecs_models_mod.DescribeKeyPairsRequest = _EcsRequest
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

    bss_pkg = types.ModuleType("alibabacloud_bssopenapi20171214")
    bss_client_mod = types.ModuleType("alibabacloud_bssopenapi20171214.client")
    bss_models_mod = types.ModuleType("alibabacloud_bssopenapi20171214.models")

    class FakeBssClient:
        """Fake BSS SDK client."""

        def __init__(self, config: Any) -> None:
            self.config = config

    bss_client_mod.Client = FakeBssClient
    bss_models_mod.QueryResourcePackageInstancesRequest = _Request
    bss_pkg.models = bss_models_mod
    register("alibabacloud_bssopenapi20171214", bss_pkg)
    register("alibabacloud_bssopenapi20171214.client", bss_client_mod)
    register("alibabacloud_bssopenapi20171214.models", bss_models_mod)

    ram_client_mod.Client = FakeRamClient
    ram_models_mod.ListUsersRequest = _Request
    ram_models_mod.ListAccessKeysRequest = _Request
    ram_models_mod.GetAccessKeyLastUsedRequest = _Request
    ram_models_mod.GetUserMFAInfoRequest = _Request
    ram_models_mod.GetUserRequest = _Request
    ram_models_mod.ListPoliciesForUserRequest = _Request
    ram_models_mod.ListGroupsForUserRequest = _Request
    ram_models_mod.GetLoginProfileRequest = _Request
    ram_pkg.models = ram_models_mod
    register("alibabacloud_ram20150501", ram_pkg)
    register("alibabacloud_ram20150501.client", ram_client_mod)
    register("alibabacloud_ram20150501.models", ram_models_mod)

    rds_pkg = types.ModuleType("alibabacloud_rds20140815")
    rds_client_mod = types.ModuleType("alibabacloud_rds20140815.client")
    rds_models_mod = types.ModuleType("alibabacloud_rds20140815.models")

    class FakeRdsClient:
        """Fake RDS SDK client."""

        def __init__(self, config: Any) -> None:
            self.config = config

    rds_client_mod.Client = FakeRdsClient
    rds_models_mod.DescribeDBInstancesRequest = _Request
    rds_models_mod.DescribeDBInstanceAttributeRequest = _Request
    rds_models_mod.DescribeDBInstanceIPArrayListRequest = _Request
    rds_models_mod.DescribeParametersRequest = _Request
    rds_models_mod.DescribeBackupPolicyRequest = _Request
    rds_models_mod.DescribeDBInstancePerformanceRequest = _Request
    rds_models_mod.DescribeSlowLogsRequest = _Request
    rds_models_mod.DescribeSlowLogRecordsRequest = _Request
    rds_models_mod.DescribeErrorLogsRequest = _Request
    rds_pkg.models = rds_models_mod
    register("alibabacloud_rds20140815", rds_pkg)
    register("alibabacloud_rds20140815.client", rds_client_mod)
    register("alibabacloud_rds20140815.models", rds_models_mod)

    kvstore_pkg = types.ModuleType("alibabacloud_r_kvstore20150101")
    kvstore_client_mod = types.ModuleType("alibabacloud_r_kvstore20150101.client")
    kvstore_models_mod = types.ModuleType("alibabacloud_r_kvstore20150101.models")

    class FakeKVStoreClient:
        """Fake KVStore SDK client."""

        def __init__(self, config: Any) -> None:
            self.config = config

    kvstore_client_mod.Client = FakeKVStoreClient
    kvstore_models_mod.DescribeInstancesRequest = _Request
    kvstore_models_mod.DescribeInstanceAttributeRequest = _Request
    kvstore_models_mod.DescribeSecurityIpsRequest = _Request
    kvstore_models_mod.DescribeParametersRequest = _Request
    kvstore_models_mod.DescribeBackupPolicyRequest = _Request
    kvstore_models_mod.DescribeSlowLogRecordsRequest = _Request
    kvstore_pkg.models = kvstore_models_mod
    register("alibabacloud_r_kvstore20150101", kvstore_pkg)
    register("alibabacloud_r_kvstore20150101.client", kvstore_client_mod)
    register("alibabacloud_r_kvstore20150101.models", kvstore_models_mod)

    vpc_pkg = types.ModuleType("alibabacloud_vpc20160428")
    vpc_client_mod = types.ModuleType("alibabacloud_vpc20160428.client")
    vpc_models_mod = types.ModuleType("alibabacloud_vpc20160428.models")

    class FakeVpcClient:
        """Fake VPC SDK client."""

        def __init__(self, config: Any) -> None:
            self.config = config

    vpc_client_mod.Client = FakeVpcClient
    vpc_models_mod.DescribeEipAddressesRequest = _Request
    vpc_models_mod.DescribeVpcsRequest = _Request
    vpc_models_mod.DescribeVSwitchesRequest = _Request
    vpc_models_mod.DescribeNatGatewaysRequest = _Request
    vpc_pkg.models = vpc_models_mod
    register("alibabacloud_vpc20160428", vpc_pkg)
    register("alibabacloud_vpc20160428.client", vpc_client_mod)
    register("alibabacloud_vpc20160428.models", vpc_models_mod)

    slb_pkg = types.ModuleType("alibabacloud_slb20140515")
    slb_client_mod = types.ModuleType("alibabacloud_slb20140515.client")
    slb_models_mod = types.ModuleType("alibabacloud_slb20140515.models")

    class FakeSlbClient:
        """Fake SLB SDK client."""

        def __init__(self, config: Any) -> None:
            self.config = config

    slb_client_mod.Client = FakeSlbClient
    slb_models_mod.DescribeLoadBalancersRequest = _Request
    slb_pkg.models = slb_models_mod
    register("alibabacloud_slb20140515", slb_pkg)
    register("alibabacloud_slb20140515.client", slb_client_mod)
    register("alibabacloud_slb20140515.models", slb_models_mod)

    sas_pkg = types.ModuleType("alibabacloud_sas20181203")
    sas_client_mod = types.ModuleType("alibabacloud_sas20181203.client")
    sas_models_mod = types.ModuleType("alibabacloud_sas20181203.models")

    class FakeSasClient:
        """Fake SAS SDK client."""

        def __init__(self, config: Any) -> None:
            self.config = config

    sas_client_mod.Client = FakeSasClient
    sas_models_mod.DescribeCheckWarningsRequest = _Request
    sas_pkg.models = sas_models_mod
    register("alibabacloud_sas20181203", sas_pkg)
    register("alibabacloud_sas20181203.client", sas_client_mod)
    register("alibabacloud_sas20181203.models", sas_models_mod)

    oss_pkg = types.ModuleType("alibabacloud_oss_v2")
    oss_client_mod = types.ModuleType("alibabacloud_oss_v2.client")
    oss_models_mod = types.ModuleType("alibabacloud_oss_v2.models")
    oss_service_mod = types.ModuleType("alibabacloud_oss_v2.models.service")
    oss_bucket_basic_mod = types.ModuleType("alibabacloud_oss_v2.models.bucket_basic")
    oss_bucket_encryption_mod = types.ModuleType("alibabacloud_oss_v2.models.bucket_encryption")
    oss_bucket_logging_mod = types.ModuleType("alibabacloud_oss_v2.models.bucket_logging")
    oss_config_mod = types.ModuleType("alibabacloud_oss_v2.config")
    oss_credentials_mod = types.ModuleType("alibabacloud_oss_v2.credentials")

    class FakeOssClient:
        """Fake OSS SDK client."""

        def __init__(self, config: Any) -> None:
            self.config = config

    class OssV2Config:
        """Fake OSS config."""

        def __init__(self, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)

    class StaticCredentialsProvider:
        """Fake static credentials provider."""

        def __init__(self, access_key_id: str, access_key_secret: str) -> None:
            self.access_key_id = access_key_id
            self.access_key_secret = access_key_secret

    oss_client_mod.Client = FakeOssClient
    oss_config_mod.Config = OssV2Config
    oss_credentials_mod.StaticCredentialsProvider = StaticCredentialsProvider
    oss_service_mod.ListBucketsRequest = _Request
    oss_bucket_basic_mod.GetBucketAclRequest = _Request
    oss_bucket_basic_mod.GetBucketVersioningRequest = _Request
    oss_bucket_basic_mod.GetBucketInfoRequest = _Request
    oss_bucket_encryption_mod.GetBucketEncryptionRequest = _Request
    oss_bucket_logging_mod.GetBucketLoggingRequest = _Request
    oss_models_mod.service = oss_service_mod
    oss_models_mod.bucket_basic = oss_bucket_basic_mod
    oss_models_mod.bucket_encryption = oss_bucket_encryption_mod
    oss_models_mod.bucket_logging = oss_bucket_logging_mod
    oss_pkg.models = oss_models_mod
    register("alibabacloud_oss_v2", oss_pkg)
    register("alibabacloud_oss_v2.client", oss_client_mod)
    register("alibabacloud_oss_v2.models", oss_models_mod)
    register("alibabacloud_oss_v2.models.service", oss_service_mod)
    register("alibabacloud_oss_v2.models.bucket_basic", oss_bucket_basic_mod)
    register("alibabacloud_oss_v2.models.bucket_encryption", oss_bucket_encryption_mod)
    register("alibabacloud_oss_v2.models.bucket_logging", oss_bucket_logging_mod)
    register("alibabacloud_oss_v2.config", oss_config_mod)
    register("alibabacloud_oss_v2.credentials", oss_credentials_mod)

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


def _load_aliyun_modules() -> tuple[Any, ...]:
    """Load and reload aliyun target modules."""
    client_mod = importlib.reload(importlib.import_module("pytbox.cloud.aliyun.client"))
    ecs_mod = importlib.reload(importlib.import_module("pytbox.cloud.aliyun.ecs"))
    cms_mod = importlib.reload(importlib.import_module("pytbox.cloud.aliyun.cms"))
    ram_mod = importlib.reload(importlib.import_module("pytbox.cloud.aliyun.ram"))
    rds_mod = importlib.reload(importlib.import_module("pytbox.cloud.aliyun.rds"))
    kvstore_mod = importlib.reload(importlib.import_module("pytbox.cloud.aliyun.kvstore"))
    bss_mod = importlib.reload(importlib.import_module("pytbox.cloud.aliyun.bss"))
    vpc_mod = importlib.reload(importlib.import_module("pytbox.cloud.aliyun.vpc"))
    slb_mod = importlib.reload(importlib.import_module("pytbox.cloud.aliyun.slb"))
    sas_mod = importlib.reload(importlib.import_module("pytbox.cloud.aliyun.sas"))
    oss_mod = importlib.reload(importlib.import_module("pytbox.cloud.aliyun.oss"))
    aliyun_mod = importlib.reload(importlib.import_module("pytbox.cloud.aliyun.aliyun"))
    return (
        client_mod,
        ecs_mod,
        cms_mod,
        ram_mod,
        rds_mod,
        kvstore_mod,
        bss_mod,
        vpc_mod,
        slb_mod,
        sas_mod,
        oss_mod,
        aliyun_mod,
    )


def test_aliyun_options_passthrough_and_retry_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aliyun options should be passed through with retry cap."""
    _install_fake_aliyun_sdk(monkeypatch)
    (
        _client_mod,
        _ecs_mod,
        _cms_mod,
        _ram_mod,
        _rds_mod,
        _kvstore_mod,
        _bss_mod,
        _vpc_mod,
        _slb_mod,
        _sas_mod,
        _oss_mod,
        aliyun_mod,
    ) = _load_aliyun_modules()

    options = aliyun_mod.AliyunOptions(
        retries=99,
        cms_endpoint="custom.cms.endpoint",
        ram_endpoint="custom.ram.endpoint",
        sls_endpoint="custom.sls.endpoint",
        rds_endpoint="custom.rds.endpoint",
        kvstore_endpoint="custom.kvstore.endpoint",
        vpc_endpoint="custom.vpc.endpoint",
        slb_endpoint="custom.slb.endpoint",
        sas_endpoint="custom.sas.endpoint",
        oss_endpoint="custom.oss.endpoint",
        bss_endpoint="custom.bss.endpoint",
    )
    ali = aliyun_mod.Aliyun(ak="ak", sk="secret-sk", region="cn-shanghai", options=options)

    assert ali._client.cfg.retries == 3
    assert ali._client.cfg.cms_endpoint == "custom.cms.endpoint"
    assert ali._client.cfg.ram_endpoint == "custom.ram.endpoint"
    assert ali._client.cfg.sls_endpoint == "custom.sls.endpoint"
    assert ali._client.cfg.rds_endpoint == "custom.rds.endpoint"
    assert ali._client.cfg.kvstore_endpoint == "custom.kvstore.endpoint"
    assert ali._client.cfg.vpc_endpoint == "custom.vpc.endpoint"
    assert ali._client.cfg.slb_endpoint == "custom.slb.endpoint"
    assert ali._client.cfg.sas_endpoint == "custom.sas.endpoint"
    assert ali._client.cfg.oss_endpoint == "custom.oss.endpoint"
    assert ali._client.cfg.bss_endpoint == "custom.bss.endpoint"
    assert hasattr(ali, "sls")
    assert hasattr(ali, "rds")
    assert hasattr(ali, "kvstore")
    assert hasattr(ali, "vpc")
    assert hasattr(ali, "slb")
    assert hasattr(ali, "sas")
    assert hasattr(ali, "oss")
    assert hasattr(ali, "bss")


def test_aliyun_client_call_retries_and_logs(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """Aliyun client call should retry timeout and emit key-step logs."""
    _install_fake_aliyun_sdk(monkeypatch)
    (
        client_mod,
        _ecs_mod,
        _cms_mod,
        _ram_mod,
        _rds_mod,
        _kvstore_mod,
        _bss_mod,
        _vpc_mod,
        _slb_mod,
        _sas_mod,
        _oss_mod,
        _aliyun_mod,
    ) = _load_aliyun_modules()

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
    (
        _client_mod,
        ecs_mod,
        _cms_mod,
        _ram_mod,
        _rds_mod,
        _kvstore_mod,
        _bss_mod,
        _vpc_mod,
        _slb_mod,
        _sas_mod,
        _oss_mod,
        _aliyun_mod,
    ) = _load_aliyun_modules()

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


def test_aliyun_ecs_count_unbound_resources(monkeypatch: pytest.MonkeyPatch) -> None:
    """ECS helper APIs should count unbound EIP and unattached disks."""
    _install_fake_aliyun_sdk(monkeypatch)
    (
        _client_mod,
        ecs_mod,
        _cms_mod,
        _ram_mod,
        _rds_mod,
        _kvstore_mod,
        _bss_mod,
        _vpc_mod,
        _slb_mod,
        _sas_mod,
        _oss_mod,
        _aliyun_mod,
    ) = _load_aliyun_modules()

    class FakeBody:
        """Fake response body."""

        def __init__(self, payload: dict[str, Any]) -> None:
            self._payload = payload

        def to_map(self) -> dict[str, Any]:
            return self._payload

    class FakeResponse:
        """Fake SDK response."""

        def __init__(self, payload: dict[str, Any]) -> None:
            self.body = FakeBody(payload)

    class FakeEcsApi:
        """Fake ECS API."""

        def __init__(self) -> None:
            self.eip_requests: list[Any] = []
            self.disk_requests: list[Any] = []

        def describe_eip_addresses(self, request: Any) -> FakeResponse:
            self.eip_requests.append(request)
            page = int(request.kwargs.get("page_number", 1))
            if page == 1:
                return FakeResponse(
                    {
                        "TotalCount": 3,
                        "EipAddresses": {
                            "EipAddress": [
                                {"AllocationId": "eip-1", "Status": "Available", "InstanceId": None},
                                {"AllocationId": "eip-2", "Status": "Available", "InstanceId": "i-1"},
                            ]
                        },
                    }
                )
            return FakeResponse(
                {
                    "TotalCount": 3,
                    "EipAddresses": {"EipAddress": [{"AllocationId": "eip-3", "Status": "Available", "InstanceId": ""}]},
                }
            )

        def describe_disks(self, request: Any) -> FakeResponse:
            self.disk_requests.append(request)
            page = int(request.kwargs.get("page_number", 1))
            if page == 1:
                return FakeResponse(
                    {
                        "TotalCount": 4,
                        "Disks": {
                            "Disk": [
                                {"DiskId": "d-1", "Status": "Available", "InstanceId": None},
                                {"DiskId": "d-2", "Status": "Available", "InstanceId": "i-2"},
                            ]
                        },
                    }
                )
            return FakeResponse(
                {
                    "TotalCount": 4,
                    "Disks": {
                        "Disk": [
                            {"DiskId": "d-3", "Status": "Available", "InstanceId": ""},
                            {"DiskId": "d-4", "Status": "Available", "InstanceId": "i-4"},
                        ]
                    },
                }
            )

    class FakeClient:
        """Fake Aliyun client."""

        def __init__(self) -> None:
            self.cfg = types.SimpleNamespace(region="cn-shanghai")
            self.ecs = FakeEcsApi()
            self.actions: list[str] = []

        def call(self, action: str, caller: Any) -> Any:
            self.actions.append(action)
            return caller()

    client = FakeClient()
    resource = ecs_mod.ECSResource(client)

    eip_resp = resource.count_unassociated_eip_addresses(region="cn-shanghai", page_size=2)
    disk_resp = resource.count_unattached_disks(region="cn-shanghai", page_size=2)

    assert eip_resp.code == 0
    assert disk_resp.code == 0
    assert eip_resp.data == {"count": 2}
    assert disk_resp.data == {"count": 2}
    assert client.actions.count("ecs_count_unassociated_eip_addresses") == 2
    assert client.actions.count("ecs_count_unattached_disks") == 2
    assert all(req.kwargs.get("status") == "Available" for req in client.ecs.eip_requests)
    assert all(req.kwargs.get("status") == "Available" for req in client.ecs.disk_requests)


def test_aliyun_ecs_read_only_helpers_return_flattened_payloads(monkeypatch: pytest.MonkeyPatch) -> None:
    """Additional ECS helpers should return flattened raw resource lists."""
    _install_fake_aliyun_sdk(monkeypatch)
    (
        _client_mod,
        ecs_mod,
        _cms_mod,
        _ram_mod,
        _rds_mod,
        _kvstore_mod,
        _bss_mod,
        _vpc_mod,
        _slb_mod,
        _sas_mod,
        _oss_mod,
        _aliyun_mod,
    ) = _load_aliyun_modules()

    class FakeBody:
        """Fake response body."""

        def __init__(self, payload: dict[str, Any]) -> None:
            self._payload = payload

        def to_map(self) -> dict[str, Any]:
            return self._payload

    class FakeResponse:
        """Fake SDK response."""

        def __init__(self, payload: dict[str, Any]) -> None:
            self.body = FakeBody(payload)

    class FakeEcsApi:
        """Fake ECS API."""

        def describe_disks(self, request: Any) -> FakeResponse:
            if request.kwargs.get("disk_ids"):
                return FakeResponse(
                    {
                        "TotalCount": 1,
                        "Disks": {"Disk": [{"DiskId": "d-1", "InstanceId": "i-1"}]},
                    }
                )
            return FakeResponse(
                {
                    "TotalCount": 1,
                    "Disks": {"Disk": [{"DiskId": "d-1", "Status": "In_use", "InstanceId": "i-1"}]},
                }
            )

        def describe_snapshots(self, _request: Any) -> FakeResponse:
            return FakeResponse(
                {
                    "TotalCount": 1,
                    "Snapshots": {"Snapshot": [{"SnapshotId": "s-1", "SourceDiskId": "d-1"}]},
                }
            )

        def describe_auto_snapshot_policy_ex(self, _request: Any) -> FakeResponse:
            return FakeResponse(
                {
                    "TotalCount": 1,
                    "AutoSnapshotPolicies": {
                        "AutoSnapshotPolicy": [{"AutoSnapshotPolicyId": "sp-1", "TimePoints": "1"}]
                    },
                }
            )

        def describe_auto_snapshot_policy_associations(self, _request: Any) -> FakeResponse:
            return FakeResponse(
                {
                    "AutoSnapshotPolicyAssociations": {
                        "AutoSnapshotPolicyAssociation": [
                            {"AutoSnapshotPolicyId": "sp-1", "DiskId": "d-1"}
                        ]
                    }
                }
            )

        def describe_security_groups(self, _request: Any) -> FakeResponse:
            return FakeResponse(
                {
                    "TotalCount": 1,
                    "SecurityGroups": {"SecurityGroup": [{"SecurityGroupId": "sg-1", "VpcId": "vpc-1"}]},
                }
            )

        def describe_security_group_attribute(self, _request: Any) -> FakeResponse:
            return FakeResponse(
                {
                    "SecurityGroupId": "sg-1",
                    "Permissions": {"Permission": [{"Direction": "ingress", "PortRange": "22/22"}]},
                }
            )

        def describe_network_interfaces(self, _request: Any) -> FakeResponse:
            return FakeResponse(
                {
                    "TotalCount": 1,
                    "NetworkInterfaceSets": {
                        "NetworkInterfaceSet": [
                            {"NetworkInterfaceId": "eni-1", "InstanceId": "i-1", "VpcId": "vpc-1"}
                        ]
                    },
                }
            )

        def describe_instances_full_status(self, _request: Any) -> FakeResponse:
            return FakeResponse(
                {
                    "TotalCount": 1,
                    "InstanceFullStatusSet": {
                        "InstanceFullStatusType": [
                            {
                                "InstanceId": "i-1",
                                "Status": {"Name": "Running"},
                                "HealthStatus": {"Name": "OK"},
                            }
                        ]
                    },
                }
            )

        def describe_instance_history_events(self, _request: Any) -> FakeResponse:
            return FakeResponse(
                {
                    "TotalCount": 1,
                    "InstanceSystemEventSet": {
                        "InstanceSystemEventType": [
                            {
                                "EventId": "e-1",
                                "InstanceId": "i-1",
                                "EventCycleStatus": {"Code": "Executing"},
                            }
                        ]
                    },
                }
            )

        def describe_cloud_assistant_status(self, _request: Any) -> FakeResponse:
            return FakeResponse(
                {
                    "TotalCount": 1,
                    "InstanceCloudAssistantStatusSet": {
                        "InstanceCloudAssistantStatus": [
                            {"InstanceId": "i-1", "CloudAssistantStatus": "true", "OSType": "Linux"}
                        ]
                    },
                }
            )

        def describe_images(self, _request: Any) -> FakeResponse:
            return FakeResponse(
                {
                    "TotalCount": 1,
                    "Images": {"Image": [{"ImageId": "img-1", "ImageName": "aliyun-linux"}]},
                }
            )

        def describe_key_pairs(self, _request: Any) -> FakeResponse:
            return FakeResponse(
                {
                    "TotalCount": 1,
                    "KeyPairs": {"KeyPair": [{"KeyPairName": "kp-1", "FingerPrint": "fp-1"}]},
                }
            )

    class FakeClient:
        """Fake Aliyun client."""

        def __init__(self) -> None:
            self.cfg = types.SimpleNamespace(region="cn-shanghai")
            self.ecs = FakeEcsApi()

        def call(self, _action: str, caller: Any) -> Any:
            return caller()

    resource = ecs_mod.ECSResource(FakeClient())

    assert resource.list_disks().data[0]["DiskId"] == "d-1"
    assert resource.get_disk("d-1").data["DiskId"] == "d-1"
    assert resource.list_snapshots().data[0]["SnapshotId"] == "s-1"
    assert resource.list_auto_snapshot_policies().data[0]["AutoSnapshotPolicyId"] == "sp-1"
    assert resource.list_auto_snapshot_policy_associations().data[0]["DiskId"] == "d-1"
    assert resource.list_security_groups().data[0]["SecurityGroupId"] == "sg-1"
    assert resource.get_security_group_attribute("sg-1").data["SecurityGroupId"] == "sg-1"
    assert resource.list_network_interfaces().data[0]["NetworkInterfaceId"] == "eni-1"
    assert resource.list_instances_full_status().data[0]["InstanceId"] == "i-1"
    assert resource.list_instance_history_events().data[0]["EventId"] == "e-1"
    assert resource.list_cloud_assistant_status().data[0]["InstanceId"] == "i-1"
    assert resource.list_images().data[0]["ImageId"] == "img-1"
    assert resource.list_key_pairs().data[0]["KeyPairName"] == "kp-1"


def test_aliyun_cms_latest_metric_point(monkeypatch: pytest.MonkeyPatch) -> None:
    """Latest metric helper should return newest timestamp point."""
    _install_fake_aliyun_sdk(monkeypatch)
    (
        _client_mod,
        _ecs_mod,
        cms_mod,
        _ram_mod,
        _rds_mod,
        _kvstore_mod,
        _bss_mod,
        _vpc_mod,
        _slb_mod,
        _sas_mod,
        _oss_mod,
        _aliyun_mod,
    ) = _load_aliyun_modules()

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
    (
        _client_mod,
        _ecs_mod,
        _cms_mod,
        ram_mod,
        _rds_mod,
        _kvstore_mod,
        _bss_mod,
        _vpc_mod,
        _slb_mod,
        _sas_mod,
        _oss_mod,
        _aliyun_mod,
    ) = _load_aliyun_modules()

    class FakeBody:
        """Fake body."""

        def to_map(self) -> dict[str, Any]:
            return {
                "Users": {"User": [{"UserName": "alice"}]},
                "AccessKeys": {"AccessKey": [{"AccessKeyId": "ak1"}]},
                "Policies": {"Policy": [{"PolicyName": "AdministratorAccess"}]},
                "Groups": {"Group": [{"GroupName": "ops"}]},
                "LoginProfile": {"MFABindRequired": True},
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

        def list_groups_for_user_with_options(self, _req: Any, runtime: Any) -> Any:
            _ = runtime
            return FakeResponse()

        def get_login_profile_with_options(self, _req: Any, runtime: Any) -> Any:
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
    assert resource.list_policies_for_user(username="alice").data == {
        "policies_for_user": [{"PolicyName": "AdministratorAccess"}]
    }
    assert resource.list_groups_for_user(username="alice").data == {"groups_for_user": [{"GroupName": "ops"}]}
    assert resource.get_login_profile(username="alice").data == {"login_profile": {"MFABindRequired": True}}


def test_aliyun_rds_kvstore_network_and_sas_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aliyun read-only wrappers should flatten RDS, KVStore, network, and SAS payloads."""
    _install_fake_aliyun_sdk(monkeypatch)
    (
        _client_mod,
        _ecs_mod,
        _cms_mod,
        _ram_mod,
        rds_mod,
        kvstore_mod,
        bss_mod,
        vpc_mod,
        slb_mod,
        sas_mod,
        _oss_mod,
        _aliyun_mod,
    ) = _load_aliyun_modules()

    class FakeBody:
        """Fake SDK body."""

        def __init__(self, payload: dict[str, Any]) -> None:
            self._payload = payload

        def to_map(self) -> dict[str, Any]:
            return self._payload

    class FakeResponse:
        """Fake SDK response."""

        def __init__(self, payload: dict[str, Any]) -> None:
            self.body = FakeBody(payload)

    class FakeRdsApi:
        """Fake RDS API."""

        def describe_dbinstances_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse(
                {
                    "TotalRecordCount": 1,
                    "Items": {"DBInstance": [{"DBInstanceId": "rm-1", "VpcId": "vpc-1"}]},
                }
            )

        def describe_dbinstance_attribute_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse(
                {
                    "Items": {"DBInstanceAttribute": [{"DBInstanceId": "rm-1", "ZoneId": "cn-a"}]},
                }
            )

        def describe_dbinstance_iparray_list_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse(
                {
                    "Items": {"DBInstanceIPArray": [{"DBInstanceIPArrayName": "default"}]},
                }
            )

        def describe_parameters_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse(
                {
                    "Engine": "MySQL",
                    "EngineVersion": "8.0",
                    "RunningParameters": {"DBInstanceParameter": [{"ParameterName": "max_connections"}]},
                    "ConfigParameters": {"DBInstanceParameter": [{"ParameterName": "innodb_buffer_pool_size"}]},
                }
            )

        def describe_backup_policy_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse({"PreferredBackupPeriod": "Monday,Tuesday"})

        def describe_dbinstance_performance_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse(
                {
                    "DBInstanceId": "rm-1",
                    "PerformanceKeys": {
                        "PerformanceKey": [
                            {
                                "Key": "MySQL_DetailedSpaceUsage",
                                "Values": {
                                    "PerformanceValue": [
                                        {"Date": "2026-03-10T00:00:00Z", "Value": "20"},
                                        {"Date": "2026-03-10T01:00:00Z", "Value": "30"},
                                    ]
                                },
                            }
                        ]
                    },
                }
            )

        def describe_slow_log_records_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse(
                {
                    "TotalRecordCount": 1,
                    "Items": {
                        "SQLSlowRecord": [
                            {
                                "ExecutionStartTime": "2026-03-10T00:10:00Z",
                                "SQLText": "select 1",
                            }
                        ]
                    },
                }
            )

        def describe_slow_logs_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse(
                {
                    "TotalRecordCount": 1,
                    "Items": {
                        "SQLSlowLog": [
                            {
                                "CreateTime": "2026-03-10T00:00:00Z",
                                "DBName": "test",
                            }
                        ]
                    },
                }
            )

        def describe_error_logs_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse(
                {
                    "TotalRecordCount": 1,
                    "Items": {
                        "ErrorLog": [
                            {
                                "CreateTime": "2026-03-10T00:20:00Z",
                                "ErrorInfo": "deadlock detected",
                            }
                        ]
                    },
                }
            )

    class FakeKVStoreApi:
        """Fake KVStore API."""

        def describe_instances_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse(
                {
                    "TotalCount": 1,
                    "Instances": {"KVStoreInstance": [{"InstanceId": "r-1", "VpcId": "vpc-1"}]},
                }
            )

        def describe_instance_attribute_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse(
                {
                    "Instances": {"DBInstanceAttribute": [{"InstanceId": "r-1", "ZoneId": "cn-a"}]},
                }
            )

        def describe_security_ips_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse(
                {
                    "SecurityIpGroups": {"SecurityIpGroup": [{"SecurityIpGroupName": "default"}]},
                }
            )

        def describe_parameters_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse(
                {
                    "Engine": "Redis",
                    "EngineVersion": "7.0",
                    "RunningParameters": {"Parameter": [{"ParameterName": "timeout"}]},
                    "ConfigParameters": {"Parameter": [{"ParameterName": "maxmemory-policy"}]},
                }
            )

        def describe_backup_policy_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse({"BackupRetentionPeriod": "7"})

        def describe_slow_log_records_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse(
                {
                    "TotalRecordCount": 1,
                    "Items": {
                        "LogRecords": [
                            {
                                "ExecuteTime": "2026-03-10T00:30:00Z",
                                "Command": "set a b",
                            }
                        ]
                    },
                }
            )

    class FakeBssApi:
        """Fake BSS API."""

        def query_resource_package_instances_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse(
                {
                    "Total": 1,
                    "Data": {
                        "TotalCount": "1",
                        "Instances": {
                            "Instance": [
                                {
                                    "InstanceId": "pkg-1",
                                    "PackageType": "Capacity",
                                    "Status": "Available",
                                    "TotalAmount": "100",
                                    "RemainingAmount": "40",
                                }
                            ]
                        },
                    },
                }
            )

    class FakeVpcApi:
        """Fake VPC API."""

        def describe_eip_addresses_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse(
                {
                    "TotalCount": 1,
                    "EipAddresses": {"EipAddress": [{"AllocationId": "eip-1", "IpAddress": "1.1.1.1"}]},
                }
            )

        def describe_vpcs_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse(
                {
                    "TotalCount": 1,
                    "Vpcs": {"Vpc": [{"VpcId": "vpc-1"}]},
                }
            )

        def describe_vswitches_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse(
                {
                    "TotalCount": 1,
                    "VSwitches": {"VSwitch": [{"VSwitchId": "vsw-1"}]},
                }
            )

        def describe_nat_gateways_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse(
                {
                    "TotalCount": 1,
                    "NatGateways": {"NatGateway": [{"NatGatewayId": "nat-1"}]},
                }
            )

    class FakeSlbApi:
        """Fake SLB API."""

        def describe_load_balancers_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse(
                {
                    "TotalCount": 1,
                    "LoadBalancers": {"LoadBalancer": [{"LoadBalancerId": "lb-1"}]},
                }
            )

    class FakeSasApi:
        """Fake SAS API."""

        def describe_check_warnings_with_options(self, _req: Any, _runtime: Any) -> Any:
            return FakeResponse(
                {
                    "TotalCount": 1,
                    "CheckWarnings": [{"CheckWarningId": 1, "Uuid": "uuid-1", "Level": "high"}],
                }
            )

    class FakeClient:
        """Fake Aliyun client."""

        def __init__(self) -> None:
            self.cfg = types.SimpleNamespace(region="cn-shanghai")
            self.rds = FakeRdsApi()
            self.kvstore = FakeKVStoreApi()
            self.bss = FakeBssApi()
            self.vpc = FakeVpcApi()
            self.slb = FakeSlbApi()
            self.sas = FakeSasApi()

        def call(self, _action: str, caller: Any) -> Any:
            return caller()

    client = FakeClient()

    rds_resource = rds_mod.RDSResource(client)
    kvstore_resource = kvstore_mod.KVStoreResource(client)
    bss_resource = bss_mod.BSSResource(client)
    vpc_resource = vpc_mod.VPCResource(client)
    slb_resource = slb_mod.SLBResource(client)
    sas_resource = sas_mod.SASResource(client)

    assert rds_resource.list_instances().data[0]["DBInstanceId"] == "rm-1"
    assert rds_resource.get_instance("rm-1").data["DBInstanceId"] == "rm-1"
    assert rds_resource.list_whitelist_groups("rm-1").data[0]["DBInstanceIPArrayName"] == "default"
    assert rds_resource.list_parameters("rm-1").data["running_parameters"][0]["ParameterName"] == "max_connections"
    assert rds_resource.get_backup_policy("rm-1").data["PreferredBackupPeriod"] == "Monday,Tuesday"
    assert rds_resource.get_instance_performance(
        "rm-1",
        key="MySQL_DetailedSpaceUsage",
        start_time="2026-03-10T00:00:00Z",
        end_time="2026-03-10T01:00:00Z",
    ).data["PerformanceKeys"]["PerformanceKey"][0]["Key"] == "MySQL_DetailedSpaceUsage"
    assert rds_resource.list_slow_log_records(
        "rm-1",
        start_time="2026-03-10T00:00:00Z",
        end_time="2026-03-10T01:00:00Z",
    ).data[0]["ExecutionStartTime"] == "2026-03-10T00:10:00Z"
    assert rds_resource.list_slow_logs(
        "rm-1",
        start_time="2026-03-10T00:00:00Z",
        end_time="2026-03-10T01:00:00Z",
    ).data[0]["CreateTime"] == "2026-03-10T00:00:00Z"
    assert rds_resource.list_error_logs(
        "rm-1",
        start_time="2026-03-10T00:00:00Z",
        end_time="2026-03-10T01:00:00Z",
    ).data[0]["ErrorInfo"] == "deadlock detected"

    assert kvstore_resource.list_instances().data[0]["InstanceId"] == "r-1"
    assert kvstore_resource.get_instance("r-1").data["InstanceId"] == "r-1"
    assert kvstore_resource.list_security_ips("r-1").data[0]["SecurityIpGroupName"] == "default"
    assert kvstore_resource.list_parameters("r-1").data["config_parameters"][0]["ParameterName"] == "maxmemory-policy"
    assert kvstore_resource.get_backup_policy("r-1").data["BackupRetentionPeriod"] == "7"
    assert kvstore_resource.list_slow_log_records(
        "r-1",
        start_time="2026-03-10T00:00:00Z",
        end_time="2026-03-10T01:00:00Z",
    ).data[0]["ExecuteTime"] == "2026-03-10T00:30:00Z"
    assert bss_resource.query_resource_package_instances(product_code="ossbag").data[0]["InstanceId"] == "pkg-1"

    assert vpc_resource.list_eips().data[0]["AllocationId"] == "eip-1"
    assert vpc_resource.list_vpcs().data[0]["VpcId"] == "vpc-1"
    assert vpc_resource.list_vswitches().data[0]["VSwitchId"] == "vsw-1"
    assert vpc_resource.list_nat_gateways().data[0]["NatGatewayId"] == "nat-1"
    assert slb_resource.list_load_balancers().data[0]["LoadBalancerId"] == "lb-1"
    assert sas_resource.list_alerts().data[0]["CheckWarningId"] == 1


def test_aliyun_oss_helpers_serialize_bucket_payloads(monkeypatch: pytest.MonkeyPatch) -> None:
    """OSS helpers should serialize bucket payloads into dicts."""
    _install_fake_aliyun_sdk(monkeypatch)
    (
        _client_mod,
        _ecs_mod,
        _cms_mod,
        _ram_mod,
        _rds_mod,
        _kvstore_mod,
        _bss_mod,
        _vpc_mod,
        _slb_mod,
        _sas_mod,
        oss_mod,
        _aliyun_mod,
    ) = _load_aliyun_modules()

    class FakeBucket:
        """Fake bucket model."""

        def __init__(self, name: str, region: str) -> None:
            self.name = name
            self.region = region

    class FakeListBucketsResult:
        """Fake list buckets result."""

        def __init__(self) -> None:
            self.buckets = [FakeBucket("bucket-a", "cn-shanghai")]
            self.is_truncated = False
            self.next_marker = None

    class FakeResult:
        """Fake generic result."""

        def __init__(self, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)

    class FakeOssApi:
        """Fake OSS API."""

        def list_buckets(self, _request: Any) -> Any:
            return FakeListBucketsResult()

        def get_bucket_info(self, _request: Any) -> Any:
            return FakeResult(bucket_info=FakeResult(name="bucket-a", region="cn-shanghai"))

        def get_bucket_acl(self, _request: Any) -> Any:
            return FakeResult(acl="public-read")

        def get_bucket_versioning(self, _request: Any) -> Any:
            return FakeResult(version_status="Enabled")

        def get_bucket_encryption(self, _request: Any) -> Any:
            return FakeResult(server_side_encryption_rule=FakeResult(sse_algorithm="AES256"))

        def get_bucket_logging(self, _request: Any) -> Any:
            return FakeResult(bucket_logging_status=FakeResult(logging_enabled=FakeResult(target_bucket="logs-bucket")))

    class FakeClient:
        """Fake Aliyun client."""

        def __init__(self) -> None:
            self.oss = FakeOssApi()

        def call(self, _action: str, caller: Any) -> Any:
            return caller()

    resource = oss_mod.OSSResource(FakeClient())

    assert resource.list_buckets().data == [{"name": "bucket-a", "region": "cn-shanghai"}]
    assert resource.get_bucket_info("bucket-a").data == {"name": "bucket-a", "region": "cn-shanghai"}
    assert resource.get_bucket_acl("bucket-a").data["acl"] == "public-read"
    assert resource.get_bucket_versioning("bucket-a").data["version_status"] == "Enabled"
    assert resource.get_bucket_encryption("bucket-a").data["server_side_encryption_rule"]["sse_algorithm"] == "AES256"
    assert (
        resource.get_bucket_logging("bucket-a").data["bucket_logging_status"]["logging_enabled"]["target_bucket"]
        == "logs-bucket"
    )
