"""Volc SDK client wrapper."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from contextlib import contextmanager
from dataclasses import dataclass
import logging
import time
from typing import Any, Callable, Iterator
import uuid

import volcenginesdkcore
import volcenginesdkecs
import volcenginesdkvolcobserve

from pytbox.cloud.volc.errors import map_volc_exception


@dataclass(frozen=True)
class VolcCreds:
    """Volc credentials.

    Attributes:
        ak: Access key id.
        sk: Access key secret.
    """

    ak: str
    sk: str


@dataclass(frozen=True)
class VolcConfig:
    """Volc client config.

    Attributes:
        region: Default region id.
        timeout_s: Timeout in seconds for each SDK call.
        retries: Retry count for retryable failures. Capped at 3.
        retry_backoff_s: Exponential backoff base seconds.
    """

    region: str
    timeout_s: float = 8.0
    retries: int = 2
    retry_backoff_s: float = 0.5


class VolcClient:
    """Volc typed SDK client entry."""

    def __init__(self, *, creds: VolcCreds, cfg: VolcConfig) -> None:
        """Initialize SDK clients.

        Args:
            creds: Credentials.
            cfg: Client configuration.
        """
        self.creds = creds
        self.cfg = cfg
        self._logger = logging.getLogger(__name__)

        conf = volcenginesdkcore.Configuration()
        conf.ak = creds.ak
        conf.sk = creds.sk
        conf.region = cfg.region

        self._api_client = volcenginesdkcore.ApiClient(conf)
        self._ecs_api: Any | None = None
        self._volcobserve_api: Any | None = None

    @property
    def api_client(self) -> Any:
        """Get shared SDK api client.

        Returns:
            Any: Volc SDK api client.
        """
        return self._api_client

    def set_region(self, region: str) -> None:
        """Set current region for API client.

        Args:
            region: Region id.
        """
        self._api_client.configuration.region = region

    @contextmanager
    def use_region(self, region: str | None) -> Iterator[None]:
        """Temporarily use an override region and restore after call.

        Args:
            region: Region override. ``None`` keeps default region.

        Yields:
            None: Context body.
        """
        previous_region = self._api_client.configuration.region
        self.set_region(region or self.cfg.region)
        try:
            yield
        finally:
            self.set_region(previous_region)

    def ecs_api(self) -> Any:
        """Get cached ECS API object.

        Returns:
            Any: ECS API instance.
        """
        if self._ecs_api is None:
            self._ecs_api = volcenginesdkecs.ECSApi(self._api_client)
        return self._ecs_api

    def volc_observe_api(self) -> Any:
        """Get cached CloudMonitor API object.

        Returns:
            Any: VolcObserve API instance.

        Raises:
            AttributeError: API class cannot be resolved from SDK package.
        """
        if self._volcobserve_api is None:
            if hasattr(volcenginesdkvolcobserve, "VOLCOBSERVEApi"):
                api_class = volcenginesdkvolcobserve.VOLCOBSERVEApi
            elif hasattr(volcenginesdkvolcobserve, "VolcObserveApi"):
                api_class = volcenginesdkvolcobserve.VolcObserveApi
            else:
                raise AttributeError("volcenginesdkvolcobserve api class not found")
            self._volcobserve_api = api_class(self._api_client)
        return self._volcobserve_api

    def _invoke_with_timeout(self, caller: Callable[[], Any]) -> Any:
        """Invoke SDK caller with timeout guard.

        Args:
            caller: Callable to execute.

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
            exc: Mapped pytbox cloud exception.

        Returns:
            bool: True when retry is allowed.
        """
        return exc.__class__.__name__ in {"ThrottledError", "TimeoutError", "UpstreamError"}

    def _log_step(self, *, task_id: str, target: str, result: str, duration_ms: int) -> None:
        """Write key-step reliability logs.

        Args:
            task_id: Generated task id.
            target: Target action and service.
            result: Result summary.
            duration_ms: Call duration in milliseconds.
        """
        self._logger.info(
            "[volc] task_id=%s target=%s result=%s duration_ms=%s",
            task_id,
            target,
            result,
            duration_ms,
        )

    def call(self, action: str, fn: Callable[[], Any]) -> Any:
        """Run SDK call with timeout, retry and mapped exceptions.

        Args:
            action: Action label for logging and error mapping.
            fn: Deferred SDK call.

        Returns:
            Any: SDK response object.

        Raises:
            Exception: Mapped pytbox cloud exception.
        """
        retries = min(max(self.cfg.retries, 0), 3)
        task_id = uuid.uuid4().hex[:8]
        target = f"volc:{action}"

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
                mapped = map_volc_exception(action, RuntimeError("timed out"))
                duration_ms = int((time.monotonic() - started_at) * 1000)
                result = f"{action}_timeout_retry" if attempt < retries else f"{action}_timeout_fail"
                self._log_step(task_id=task_id, target=target, result=result, duration_ms=duration_ms)
                if attempt < retries and self._is_retryable_error(mapped):
                    time.sleep(self.cfg.retry_backoff_s * (2**attempt))
                    continue
                raise mapped from exc
            except Exception as exc:  # noqa: BLE001
                mapped = map_volc_exception(action, exc)
                duration_ms = int((time.monotonic() - started_at) * 1000)
                result = f"{action}_retry" if attempt < retries else f"{action}_fail"
                self._log_step(task_id=task_id, target=target, result=result, duration_ms=duration_ms)
                if attempt < retries and self._is_retryable_error(mapped):
                    time.sleep(self.cfg.retry_backoff_s * (2**attempt))
                    continue
                raise mapped from exc

        raise map_volc_exception(action, RuntimeError("unknown volc call failure"))
