"""Aliyun SDK client wrapper."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
import logging
import time
from typing import Any, Callable
import uuid

from alibabacloud_cms20190101.client import Client as Cms20190101Client
from alibabacloud_bssopenapi20171214.client import Client as BssOpenApi20171214Client
from alibabacloud_ecs20140526 import client as ecs_client
from alibabacloud_ram20150501.client import Client as Ram20150501Client
from alibabacloud_r_kvstore20150101.client import Client as KVStore20150101Client
from alibabacloud_rds20140815.client import Client as Rds20140815Client
from alibabacloud_sas20181203.client import Client as Sas20181203Client
from alibabacloud_slb20140515.client import Client as Slb20140515Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_vpc20160428.client import Client as Vpc20160428Client
from alibabacloud_oss_v2.client import Client as OssV2Client
from alibabacloud_oss_v2.config import Config as OssV2Config
from alibabacloud_oss_v2.credentials import StaticCredentialsProvider

from pytbox.cloud.aliyun.errors import map_tea_exception


@dataclass(frozen=True)
class AliyunCreds:
    """Aliyun credentials.

    Attributes:
        ak: Access key id.
        sk: Access key secret.
    """

    ak: str
    sk: str


@dataclass(frozen=True)
class AliyunConfig:
    """Aliyun client config.

    Attributes:
        region: Default region id.
        timeout_s: Timeout in seconds for each SDK invocation.
        retries: Retry count for retryable calls. Capped at 3.
        retry_backoff_s: Exponential backoff base seconds.
        ecs_endpoint: Optional custom ECS endpoint.
        cms_endpoint: Optional custom CMS endpoint.
        ram_endpoint: Optional custom RAM endpoint.
        sls_endpoint: Optional custom SLS endpoint.
        rds_endpoint: Optional custom RDS endpoint.
        kvstore_endpoint: Optional custom KVStore endpoint.
        vpc_endpoint: Optional custom VPC endpoint.
        slb_endpoint: Optional custom SLB endpoint.
        sas_endpoint: Optional custom Security Center endpoint.
        oss_endpoint: Optional custom OSS endpoint.
        bss_endpoint: Optional custom BSS endpoint.
    """

    region: str
    timeout_s: float = 8.0
    retries: int = 2
    retry_backoff_s: float = 0.5
    ecs_endpoint: str | None = None
    cms_endpoint: str | None = None
    ram_endpoint: str | None = None
    sls_endpoint: str | None = None
    rds_endpoint: str | None = None
    kvstore_endpoint: str | None = None
    vpc_endpoint: str | None = None
    slb_endpoint: str | None = None
    sas_endpoint: str | None = None
    oss_endpoint: str | None = None
    bss_endpoint: str | None = None


class AliyunClient:
    """Aliyun typed SDK client entry."""

    def __init__(self, *, creds: AliyunCreds, cfg: AliyunConfig) -> None:
        """Initialize SDK clients.

        Args:
            creds: Credentials.
            cfg: Client configuration.
        """
        self.creds = creds
        self.cfg = cfg
        self._logger = logging.getLogger(__name__)
        self._ecs = self._create_ecs_client()
        self._cms = self._create_cms_client()
        self._ram = self._create_ram_client()
        self._rds = self._create_rds_client()
        self._kvstore = self._create_kvstore_client()
        self._vpc = self._create_vpc_client()
        self._slb = self._create_slb_client()
        self._sas = self._create_sas_client()
        self._oss = self._create_oss_client()
        self._bss = self._create_bss_client()

    def _build_openapi_config(self) -> open_api_models.Config:
        """Build base OpenAPI config for sub-clients.

        Returns:
            open_api_models.Config: Base SDK config.
        """
        return open_api_models.Config(
            access_key_id=self.creds.ak,
            access_key_secret=self.creds.sk,
            region_id=self.cfg.region,
        )

    def _create_ecs_client(self) -> ecs_client.Client:
        """Create ECS client.

        Returns:
            ecs_client.Client: ECS SDK client.
        """
        config = self._build_openapi_config()
        if self.cfg.ecs_endpoint:
            config.endpoint = self.cfg.ecs_endpoint
        return ecs_client.Client(config)

    def _create_cms_client(self) -> Cms20190101Client:
        """Create CMS client.

        Returns:
            Cms20190101Client: CMS SDK client.
        """
        config = self._build_openapi_config()
        if self.cfg.cms_endpoint:
            config.endpoint = self.cfg.cms_endpoint
        return Cms20190101Client(config)

    def _create_ram_client(self) -> Ram20150501Client:
        """Create RAM client.

        Returns:
            Ram20150501Client: RAM SDK client.
        """
        config = self._build_openapi_config()
        if self.cfg.ram_endpoint:
            config.endpoint = self.cfg.ram_endpoint
        return Ram20150501Client(config)

    def _create_rds_client(self) -> Rds20140815Client:
        """Create RDS client.

        Returns:
            Rds20140815Client: RDS SDK client.
        """
        config = self._build_openapi_config()
        if self.cfg.rds_endpoint:
            config.endpoint = self.cfg.rds_endpoint
        return Rds20140815Client(config)

    def _create_kvstore_client(self) -> KVStore20150101Client:
        """Create KVStore client.

        Returns:
            KVStore20150101Client: KVStore SDK client.
        """
        config = self._build_openapi_config()
        if self.cfg.kvstore_endpoint:
            config.endpoint = self.cfg.kvstore_endpoint
        return KVStore20150101Client(config)

    def _create_vpc_client(self) -> Vpc20160428Client:
        """Create VPC client.

        Returns:
            Vpc20160428Client: VPC SDK client.
        """
        config = self._build_openapi_config()
        if self.cfg.vpc_endpoint:
            config.endpoint = self.cfg.vpc_endpoint
        return Vpc20160428Client(config)

    def _create_slb_client(self) -> Slb20140515Client:
        """Create SLB client.

        Returns:
            Slb20140515Client: SLB SDK client.
        """
        config = self._build_openapi_config()
        if self.cfg.slb_endpoint:
            config.endpoint = self.cfg.slb_endpoint
        return Slb20140515Client(config)

    def _create_sas_client(self) -> Sas20181203Client:
        """Create Security Center client.

        Returns:
            Sas20181203Client: SAS SDK client.
        """
        config = self._build_openapi_config()
        if self.cfg.sas_endpoint:
            config.endpoint = self.cfg.sas_endpoint
        return Sas20181203Client(config)

    def _create_oss_client(self) -> OssV2Client:
        """Create OSS client.

        Returns:
            OssV2Client: OSS v2 SDK client.
        """
        endpoint = self.cfg.oss_endpoint or f"oss-{self.cfg.region}.aliyuncs.com"
        config = OssV2Config(
            region=self.cfg.region,
            endpoint=endpoint,
            credentials_provider=StaticCredentialsProvider(
                self.creds.ak,
                self.creds.sk,
            ),
            retry_max_attempts=min(max(self.cfg.retries, 0), 3) + 1,
            connect_timeout=self.cfg.timeout_s,
            readwrite_timeout=self.cfg.timeout_s,
        )
        return OssV2Client(config)

    def _create_bss_client(self) -> BssOpenApi20171214Client:
        """Create BSS client.

        Returns:
            BssOpenApi20171214Client: BSS SDK client.
        """
        config = self._build_openapi_config()
        if self.cfg.bss_endpoint:
            config.endpoint = self.cfg.bss_endpoint
        return BssOpenApi20171214Client(config)

    @property
    def ecs(self) -> ecs_client.Client:
        """Get ECS client.

        Returns:
            ecs_client.Client: ECS SDK client.
        """
        return self._ecs

    @property
    def cms(self) -> Cms20190101Client:
        """Get CMS client.

        Returns:
            Cms20190101Client: CMS SDK client.
        """
        return self._cms

    @property
    def ram(self) -> Ram20150501Client:
        """Get RAM client.

        Returns:
            Ram20150501Client: RAM SDK client.
        """
        return self._ram

    @property
    def rds(self) -> Rds20140815Client:
        """Get RDS client.

        Returns:
            Rds20140815Client: RDS SDK client.
        """
        return self._rds

    @property
    def kvstore(self) -> KVStore20150101Client:
        """Get KVStore client.

        Returns:
            KVStore20150101Client: KVStore SDK client.
        """
        return self._kvstore

    @property
    def vpc(self) -> Vpc20160428Client:
        """Get VPC client.

        Returns:
            Vpc20160428Client: VPC SDK client.
        """
        return self._vpc

    @property
    def slb(self) -> Slb20140515Client:
        """Get SLB client.

        Returns:
            Slb20140515Client: SLB SDK client.
        """
        return self._slb

    @property
    def sas(self) -> Sas20181203Client:
        """Get Security Center client.

        Returns:
            Sas20181203Client: SAS SDK client.
        """
        return self._sas

    @property
    def oss(self) -> OssV2Client:
        """Get OSS client.

        Returns:
            OssV2Client: OSS SDK client.
        """
        return self._oss

    @property
    def bss(self) -> BssOpenApi20171214Client:
        """Get BSS client.

        Returns:
            BssOpenApi20171214Client: BSS SDK client.
        """
        return self._bss

    def _invoke_with_timeout(self, caller: Callable[[], Any]) -> Any:
        """Invoke an SDK caller with timeout protection.

        Args:
            caller: Callable that executes SDK operation.

        Returns:
            Any: SDK response.
        """
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(caller)
            return future.result(timeout=self.cfg.timeout_s)

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        """Check whether mapped exception is retryable.

        Args:
            exc: Mapped pytbox exception.

        Returns:
            bool: True when retry is allowed.
        """
        return exc.__class__.__name__ in {"ThrottledError", "TimeoutError", "UpstreamError"}

    def _log_step(self, *, task_id: str, target: str, result: str, duration_ms: int) -> None:
        """Write reliability logs for key steps.

        Args:
            task_id: Generated task id.
            target: Target action and service.
            result: Result summary.
            duration_ms: Call duration in milliseconds.
        """
        self._logger.info(
            "[aliyun] task_id=%s target=%s result=%s duration_ms=%s",
            task_id,
            target,
            result,
            duration_ms,
        )

    def call(self, action: str, fn: Callable[[], Any]) -> Any:
        """Call SDK with timeout, retry, and mapped exceptions.

        Args:
            action: Action label for error mapping and logging.
            fn: Deferred SDK call.

        Returns:
            Any: SDK response object.

        Raises:
            Exception: Mapped pytbox cloud exception.
        """
        retries = min(max(self.cfg.retries, 0), 3)
        task_id = uuid.uuid4().hex[:8]
        target = f"aliyun:{action}"

        for attempt in range(retries + 1):
            started_at = time.monotonic()
            try:
                response = self._invoke_with_timeout(fn)
                duration_ms = int((time.monotonic() - started_at) * 1000)
                self._log_step(
                    task_id=task_id,
                    target=target,
                    result=f"{action}_ok",
                    duration_ms=duration_ms,
                )
                return response
            except FutureTimeoutError as exc:
                mapped = map_tea_exception(action, RuntimeError("timed out"))
                duration_ms = int((time.monotonic() - started_at) * 1000)
                result = f"{action}_timeout_retry" if attempt < retries else f"{action}_timeout_fail"
                self._log_step(task_id=task_id, target=target, result=result, duration_ms=duration_ms)
                if attempt < retries and self._is_retryable_error(mapped):
                    time.sleep(self.cfg.retry_backoff_s * (2**attempt))
                    continue
                raise mapped from exc
            except Exception as exc:  # noqa: BLE001
                mapped = map_tea_exception(action, exc)
                duration_ms = int((time.monotonic() - started_at) * 1000)
                result = f"{action}_retry" if attempt < retries else f"{action}_fail"
                self._log_step(task_id=task_id, target=target, result=result, duration_ms=duration_ms)
                if attempt < retries and self._is_retryable_error(mapped):
                    time.sleep(self.cfg.retry_backoff_s * (2**attempt))
                    continue
                raise mapped from exc

        raise map_tea_exception(action, RuntimeError("unknown aliyun call failure"))
