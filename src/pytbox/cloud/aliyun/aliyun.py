"""Aliyun cloud module entrypoint."""

from __future__ import annotations

from dataclasses import dataclass

from pytbox.cloud.aliyun.client import AliyunClient, AliyunConfig, AliyunCreds
from pytbox.cloud.aliyun.bss import BSSResource
from pytbox.cloud.aliyun.cms import CMSResource
from pytbox.cloud.aliyun.ecs import ECSResource
from pytbox.cloud.aliyun.kvstore import KVStoreResource
from pytbox.cloud.aliyun.oss import OSSResource
from pytbox.cloud.aliyun.ram import RAMResource
from pytbox.cloud.aliyun.rds import RDSResource
from pytbox.cloud.aliyun.sas import SASResource
from pytbox.cloud.aliyun.slb import SLBResource
from pytbox.cloud.aliyun.sls import SLSResource
from pytbox.cloud.aliyun.vpc import VPCResource


@dataclass(frozen=True)
class AliyunOptions:
    """Aliyun runtime options.

    Attributes:
        timeout_s: Timeout in seconds for each SDK call.
        retries: Retry count for retryable failures. Capped to 3.
        retry_backoff_s: Base backoff seconds for linear retry sleep.
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


class Aliyun:
    """Aliyun resource aggregator.

    Example:
        ali = Aliyun(ak="ak", sk="sk", region="cn-hangzhou")
        ali.ecs.list()
        ali.cms.cpu_utilization(instance_id="i-xx", start_ts=1, end_ts=2)
    """

    def __init__(
        self,
        *,
        ak: str,
        sk: str,
        region: str,
        options: AliyunOptions | None = None,
    ) -> None:
        """Initialize Aliyun facade.

        Args:
            ak: Aliyun access key.
            sk: Aliyun secret key.
            region: Default region id.
            options: Runtime options.
        """
        opt = options or AliyunOptions()
        retries = min(max(opt.retries, 0), 3)
        cms_endpoint = opt.cms_endpoint or f"metrics.{region}.aliyuncs.com"

        self._client = AliyunClient(
            creds=AliyunCreds(ak=ak, sk=sk),
            cfg=AliyunConfig(
                region=region,
                timeout_s=opt.timeout_s,
                retries=retries,
                retry_backoff_s=opt.retry_backoff_s,
                ecs_endpoint=opt.ecs_endpoint,
                cms_endpoint=cms_endpoint,
                ram_endpoint=opt.ram_endpoint,
                sls_endpoint=opt.sls_endpoint,
                rds_endpoint=opt.rds_endpoint,
                kvstore_endpoint=opt.kvstore_endpoint,
                vpc_endpoint=opt.vpc_endpoint,
                slb_endpoint=opt.slb_endpoint,
                sas_endpoint=opt.sas_endpoint,
                oss_endpoint=opt.oss_endpoint,
                bss_endpoint=opt.bss_endpoint,
            ),
        )
        self.ecs = ECSResource(self._client)
        self.cms = CMSResource(self._client)
        self.ram = RAMResource(self._client)
        self.rds = RDSResource(self._client)
        self.kvstore = KVStoreResource(self._client)
        self.vpc = VPCResource(self._client)
        self.slb = SLBResource(self._client)
        self.sas = SASResource(self._client)
        self.oss = OSSResource(self._client)
        self.sls = SLSResource(self._client)
        self.bss = BSSResource(self._client)
