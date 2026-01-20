from dataclasses import dataclass

from pytbox.cloud.aliyun.client import AliyunClient, AliyunCreds, AliyunConfig
from pytbox.cloud.aliyun.ecs import ECSResource
from pytbox.cloud.aliyun.cms import CMSResource
from pytbox.cloud.aliyun.ram import RAMResource


@dataclass(frozen=True)
class AliyunOptions:
    timeout_s: float = 8.0
    retries: int = 1
    retry_backoff_s: float = 0.5
    ecs_endpoint: str | None = None
    cms_endpoint: str | None = None


class Aliyun:
    """
    使用方式：
        ali = Aliyun(ak="..", sk="..", region="cn-hangzhou")
        ali.ecs.list()
        ali.cms.cpu_utilization(...)
    """

    def __init__(
        self,
        *,
        ak: str,
        sk: str,
        region: str,
        options: AliyunOptions | None = None,
    ) -> None:
        opt = options or AliyunOptions()

        self._client = AliyunClient(
            creds=AliyunCreds(ak=ak, sk=sk),
            cfg=AliyunConfig(
                region=region,
                timeout_s=opt.timeout_s,
                retries=opt.retries,
                retry_backoff_s=opt.retry_backoff_s,
                ecs_endpoint=opt.ecs_endpoint,
                cms_endpoint=f'metrics.{region}.aliyuncs.com',
            ),
        )

        self.ecs = ECSResource(self._client)
        self.cms = CMSResource(self._client)
        self.ram = RAMResource(self._client)
