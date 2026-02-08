"""Volc cloud module entrypoint."""

from __future__ import annotations

from dataclasses import dataclass

from pytbox.cloud.volc.client import VolcClient, VolcConfig, VolcCreds
from pytbox.cloud.volc.cloudmonitor import CloudMonitorResource
from pytbox.cloud.volc.ecs import ECSResource


@dataclass(frozen=True)
class VolcOptions:
    """Volc runtime options.

    Attributes:
        timeout_s: Timeout in seconds for each SDK invocation.
        retries: Retry count for retryable calls. Capped at 3.
        retry_backoff_s: Exponential backoff base seconds.
    """

    timeout_s: float = 8.0
    retries: int = 2
    retry_backoff_s: float = 0.5


class Volc:
    """Volc resource aggregator."""

    def __init__(self, *, ak: str, sk: str, region: str, options: VolcOptions | None = None) -> None:
        """Initialize Volc facade.

        Args:
            ak: Volc access key.
            sk: Volc secret key.
            region: Default region id.
            options: Runtime options.
        """
        opt = options or VolcOptions()
        retries = min(max(opt.retries, 0), 3)

        self._client = VolcClient(
            creds=VolcCreds(ak=ak, sk=sk),
            cfg=VolcConfig(
                region=region,
                timeout_s=opt.timeout_s,
                retries=retries,
                retry_backoff_s=opt.retry_backoff_s,
            ),
        )
        self.ecs = ECSResource(self._client)
        self.cloudmonitor = CloudMonitorResource(self._client)
