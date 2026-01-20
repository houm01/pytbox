import time
from dataclasses import dataclass

from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_ecs20140526 import client as ecs_client
from alibabacloud_cms20190101.client import Client as Cms20190101Client
from alibabacloud_ram20150501.client import Client as Ram20150501Client
from Tea.exceptions import TeaException

from pytbox.cloud.aliyun.errors import map_tea_exception


@dataclass(frozen=True)
class AliyunCreds:
    ak: str
    sk: str


@dataclass(frozen=True)
class AliyunConfig:
    region: str
    timeout_s: float = 8.0
    retries: int = 1
    retry_backoff_s: float = 0.5
    ecs_endpoint: str | None = None
    cms_endpoint: str | None = None
    ram_endpoint: str | None = None


class AliyunClient:
    def __init__(self, *, creds: AliyunCreds, cfg: AliyunConfig):
        self.creds = creds
        self.cfg = cfg
        self._ecs = self._create_ecs_client()
        self._cms = self._create_cms_client()
        self._ram = self._create_ram_client()

    def _create_ecs_client(self) -> ecs_client.Client:
        config = open_api_models.Config(
            access_key_id=self.creds.ak,
            access_key_secret=self.creds.sk,
            region_id=self.cfg.region,
        )
        if self.cfg.ecs_endpoint:
            config.endpoint = self.cfg.ecs_endpoint
        return ecs_client.Client(config)

    def _create_cms_client(self) -> Cms20190101Client:
        config = open_api_models.Config(
            access_key_id=self.creds.ak,
            access_key_secret=self.creds.sk,
            region_id=self.cfg.region,
        )
        if self.cfg.cms_endpoint:
            config.endpoint = self.cfg.cms_endpoint
        return Cms20190101Client(config)

    def _create_ram_client(self) -> Ram20150501Client:
        config = open_api_models.Config(
            access_key_id=self.creds.ak,
            access_key_secret=self.creds.sk,
            region_id=self.cfg.region,
        )
        if self.cfg.ram_endpoint:
            config.endpoint = self.cfg.ram_endpoint
        return Ram20150501Client(config)

    @property
    def ecs(self) -> ecs_client.Client:
        return self._ecs

    @property
    def cms(self) -> Cms20190101Client:
        return self._cms

    @property
    def ram(self) -> Ram20150501Client:
        return self._ram

    def call(self, action: str, fn):
        """
        统一入口：重试 + TeaException 映射为 pytbox 异常
        """
        last_exc: Exception | None = None
        for attempt in range(self.cfg.retries + 1):
            try:
                return fn()
            except Exception as e:  # noqa: BLE001
                last_exc = e
                mapped = map_tea_exception(action, e)

                # 只有限流/超时/上游不稳定，才值得重试（你也可按需扩展）
                retryable = mapped.__class__.__name__ in {"ThrottledError", "TimeoutError", "UpstreamError"}
                if attempt < self.cfg.retries and retryable:
                    time.sleep(self.cfg.retry_backoff_s * (attempt + 1))
                    continue
                raise mapped from e

        raise map_tea_exception(action, last_exc or Exception("unknown"))
