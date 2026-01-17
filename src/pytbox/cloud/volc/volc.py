from dataclasses import dataclass

from pytbox.cloud.volc.client import VolcClient, VolcCreds, VolcConfig
from pytbox.cloud.volc.ecs import ECSResource
from pytbox.cloud.volc.cloudmonitor import CloudMonitorResource


@dataclass(frozen=True)
class VolcOptions:
    timeout_s: float = 8.0
    # volcengine-python-sdk 里常用 configuration.region
    # 其他参数后续再加：endpoint、scheme、retries...


class Volc:
    """
    用法：
        ve = Volc(ak="..", sk="..", region="cn-beijing")
        ve.ecs.list()                    # 默认 region
        ve.ecs.list(region="cn-shanghai")
        ve.cloudmonitor.get_metric_data(...)
    """

    def __init__(self, *, ak: str, sk: str, region: str, options: VolcOptions | None = None):
        opt = options or VolcOptions()

        self._client = VolcClient(
            creds=VolcCreds(ak=ak, sk=sk),
            cfg=VolcConfig(region=region, timeout_s=opt.timeout_s),
        )

        self.ecs = ECSResource(self._client)
        self.cloudmonitor = CloudMonitorResource(self._client)
