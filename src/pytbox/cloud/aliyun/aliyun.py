"""Aliyun cloud module entrypoint."""

from __future__ import annotations

from dataclasses import dataclass

from pytbox.cloud.aliyun.client import AliyunClient, AliyunConfig, AliyunCreds
from pytbox.cloud.aliyun.cms import CMSResource
from pytbox.cloud.aliyun.ecs import ECSResource
from pytbox.cloud.aliyun.ram import RAMResource


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
    """

    timeout_s: float = 8.0
    retries: int = 2
    retry_backoff_s: float = 0.5
    ecs_endpoint: str | None = None
    cms_endpoint: str | None = None
    ram_endpoint: str | None = None


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
            ),
        )
        self.ecs = ECSResource(self._client)
        self.cms = CMSResource(self._client)
        self.ram = RAMResource(self._client)
