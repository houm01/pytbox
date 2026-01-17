import volcenginesdkcore
import volcenginesdkecs
import volcenginesdkvolcobserve

from dataclasses import dataclass
from pytbox.cloud.volc.errors import map_volc_exception


@dataclass(frozen=True)
class VolcCreds:
    ak: str
    sk: str


@dataclass(frozen=True)
class VolcConfig:
    region: str
    timeout_s: float = 8.0


class VolcClient:
    def __init__(self, *, creds: VolcCreds, cfg: VolcConfig):
        self.creds = creds
        self.cfg = cfg

        conf = volcenginesdkcore.Configuration()
        conf.ak = creds.ak
        conf.sk = creds.sk
        conf.region = cfg.region

        self._api_client = volcenginesdkcore.ApiClient(conf)

        # API 实例做缓存（避免重复创建）
        self._ecs_api = None
        self._volcobserve_api = None

    @property
    def api_client(self):
        return self._api_client

    def set_region(self, region: str) -> None:
        self._api_client.configuration.region = region

    def ecs_api(self):
        if self._ecs_api is None:
            self._ecs_api = volcenginesdkecs.ECSApi(self._api_client)
        return self._ecs_api

    def volc_observe_api(self):
        if self._volcobserve_api is None:
            # volcobserve 的 api 类名通常是 VOLCOBSERVEApi（按你安装版本可能不同）
            # 这里做一层兼容
            if hasattr(volcenginesdkvolcobserve, "VOLCOBSERVEApi"):
                ApiCls = volcenginesdkvolcobserve.VOLCOBSERVEApi
            elif hasattr(volcenginesdkvolcobserve, "VolcObserveApi"):
                ApiCls = volcenginesdkvolcobserve.VolcObserveApi
            else:
                # 最后兜底：有些版本叫 VOLCOBSERVEApi/ VOLCOBSERVEApi
                # 如果这里报错，把 dir(volcenginesdkvolcobserve) 里 api 类名贴我
                raise AttributeError("volcenginesdkvolcobserve api class not found")
            self._volcobserve_api = ApiCls(self._api_client)
        return self._volcobserve_api

    def call(self, action: str, fn):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            raise map_volc_exception(action, e) from e