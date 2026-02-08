"""Aliyun CMS resource operations."""

from __future__ import annotations

from datetime import datetime
import json
import time
from typing import Any

from alibabacloud_cms20190101 import models as cms_models
from alibabacloud_tea_util import models as util_models
import pytz

from ...schemas.response import ReturnResponse


class CMSResource:
    """Aliyun CloudMonitor resource wrapper."""

    def __init__(self, client: Any) -> None:
        """Initialize resource.

        Args:
            client: AliyunClient instance.
        """
        self._c = client
        self._tz = pytz.timezone("Asia/Shanghai")

    def _format_cms_time(self, timestamp_s: int) -> str:
        """Format unix timestamp to Aliyun CMS datetime string.

        Args:
            timestamp_s: Unix timestamp in seconds.

        Returns:
            str: ``YYYY-mm-dd HH:MM:SS`` in Asia/Shanghai timezone.
        """
        return datetime.fromtimestamp(timestamp_s, self._tz).strftime("%Y-%m-%d %H:%M:%S")

    def _normalize_dimensions(self, dimensions: dict[str, Any] | list[dict[str, Any]] | str) -> str:
        """Normalize dimensions input into JSON string.

        Args:
            dimensions: Dimensions in dict/list-json/string format.

        Returns:
            str: JSON string accepted by Aliyun CMS SDK.
        """
        if isinstance(dimensions, str):
            return dimensions
        if isinstance(dimensions, dict):
            return json.dumps([dimensions])
        if isinstance(dimensions, list):
            return json.dumps(dimensions)
        raise TypeError("dimensions must be dict, list[dict], or str")

    def _resolve_window(
        self,
        *,
        start_time: int | str | None,
        end_time: int | str | None,
        last_minute: int | None,
    ) -> tuple[str, str]:
        """Resolve query time window strings.

        Args:
            start_time: Start timestamp in seconds or formatted datetime string.
            end_time: End timestamp in seconds or formatted datetime string.
            last_minute: Rolling window in minutes.

        Returns:
            tuple[str, str]: Start and end datetime strings.
        """
        if last_minute is not None:
            now_s = int(time.time())
            start_s = now_s - (last_minute * 60)
            return self._format_cms_time(start_s), self._format_cms_time(now_s)

        if start_time is None or end_time is None:
            raise ValueError("Provide either last_minute or both start_time and end_time.")

        if isinstance(start_time, int):
            start_str = self._format_cms_time(start_time)
        else:
            start_str = start_time
        if isinstance(end_time, int):
            end_str = self._format_cms_time(end_time)
        else:
            end_str = end_time
        return start_str, end_str

    @staticmethod
    def _safe_json_list(raw_data: str | None) -> list[dict[str, Any]]:
        """Parse JSON datapoints into list payload.

        Args:
            raw_data: Raw datapoints string from SDK response.

        Returns:
            list[dict[str, Any]]: Parsed datapoints list.
        """
        if not raw_data:
            return []
        try:
            parsed = json.loads(raw_data)
        except Exception:  # noqa: BLE001
            return []
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        return []

    @staticmethod
    def _extract_value(point: dict[str, Any]) -> float | None:
        """Extract a numeric metric value from a datapoint.

        Args:
            point: Metric datapoint.

        Returns:
            float | None: Parsed value if available.
        """
        for key in ("Average", "Value", "value", "Maximum", "Minimum"):
            value = point.get(key)
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
        return None

    @staticmethod
    def _extract_ts_seconds(point: dict[str, Any]) -> int | None:
        """Extract timestamp in seconds from datapoint.

        Args:
            point: Metric datapoint.

        Returns:
            int | None: Timestamp in seconds.
        """
        for key in ("timestamp", "Timestamp", "ts"):
            value = point.get(key)
            if value is None:
                continue
            try:
                ts = int(value)
            except (TypeError, ValueError):
                return None
            if ts > 10_000_000_000:
                return ts // 1000
            return ts
        return None

    def get_metric_data_resp(
        self,
        *,
        namespace: str,
        metric_name: str,
        dimensions: dict[str, Any] | list[dict[str, Any]] | str,
        start_time: int | str | None = None,
        end_time: int | str | None = None,
        last_minute: int | None = None,
    ) -> ReturnResponse:
        """Fetch metric datapoints as ``ReturnResponse``.

        Args:
            namespace: Metric namespace.
            metric_name: Metric name.
            dimensions: Dimension definitions.
            start_time: Start time in seconds or formatted datetime string.
            end_time: End time in seconds or formatted datetime string.
            last_minute: Optional rolling window in minutes.

        Returns:
            ReturnResponse: ``data`` is list of metric datapoints.
        """
        dimensions_str = self._normalize_dimensions(dimensions)
        start_str, end_str = self._resolve_window(
            start_time=start_time,
            end_time=end_time,
            last_minute=last_minute,
        )
        req = cms_models.DescribeMetricLastRequest(
            namespace=namespace,
            metric_name=metric_name,
            dimensions=dimensions_str,
            start_time=start_str,
            end_time=end_str,
        )
        runtime = util_models.RuntimeOptions()
        resp = self._c.call(
            "cms_get_metric_data",
            lambda: self._c.cms.describe_metric_last_with_options(req, runtime=runtime),
        )
        body = getattr(resp, "body", None)
        datapoints_raw = getattr(body, "datapoints", None)
        points = self._safe_json_list(datapoints_raw)
        return ReturnResponse(code=0, msg="success", data=points)

    def get_metric_data(
        self,
        *,
        namespace: str,
        metric_name: str,
        dimensions: dict[str, Any] | list[dict[str, Any]] | str,
        start_time: int | str | None = None,
        end_time: int | str | None = None,
        last_minute: int | None = None,
    ) -> list[dict[str, Any]]:
        """Backward-compatible metric query that returns raw datapoint list.

        Args:
            namespace: Metric namespace.
            metric_name: Metric name.
            dimensions: Dimension definitions.
            start_time: Start time in seconds or formatted datetime string.
            end_time: End time in seconds or formatted datetime string.
            last_minute: Optional rolling window in minutes.

        Returns:
            list[dict[str, Any]]: Parsed datapoints.
        """
        response = self.get_metric_data_resp(
            namespace=namespace,
            metric_name=metric_name,
            dimensions=dimensions,
            start_time=start_time,
            end_time=end_time,
            last_minute=last_minute,
        )
        return response.data if isinstance(response.data, list) else []

    def cpu_utilization_resp(
        self,
        *,
        instance_id: str,
        start_ts: int,
        end_ts: int,
        period_s: int = 60,
    ) -> ReturnResponse:
        """Fetch ECS CPU utilization points.

        Args:
            instance_id: ECS instance id.
            start_ts: Start unix timestamp in seconds.
            end_ts: End unix timestamp in seconds.
            period_s: Metric period in seconds.

        Returns:
            ReturnResponse: ``data`` is normalized ``[{ts, value}, ...]`` list.
        """
        if end_ts < start_ts:
            return ReturnResponse(code=1, msg="end_ts must be greater than start_ts", data=None)

        dimensions = json.dumps([{"instanceId": instance_id}])
        req = cms_models.DescribeMetricListRequest(
            namespace="acs_ecs_dashboard",
            metric_name="CPUUtilization",
            dimensions=dimensions,
            start_time=start_ts * 1000,
            end_time=end_ts * 1000,
            period=str(period_s),
        )
        resp = self._c.call(
            "cms_cpu_utilization",
            lambda: self._c.cms.describe_metric_list(req),
        )
        body = getattr(resp, "body", None)
        points = self._safe_json_list(getattr(body, "datapoints", None))
        normalized: list[dict[str, float | int]] = []
        for point in points:
            ts = self._extract_ts_seconds(point)
            value = self._extract_value(point)
            if ts is None or value is None:
                continue
            normalized.append({"ts": ts, "value": value})
        return ReturnResponse(code=0, msg="success", data=normalized)

    def cpu_utilization(
        self,
        *,
        instance_id: str,
        start_ts: int,
        end_ts: int,
        period_s: int = 60,
    ) -> list[dict[str, float | int]]:
        """Backward-compatible CPU utilization query.

        Args:
            instance_id: ECS instance id.
            start_ts: Start unix timestamp in seconds.
            end_ts: End unix timestamp in seconds.
            period_s: Metric period in seconds.

        Returns:
            list[dict[str, float | int]]: Normalized metric points.
        """
        response = self.cpu_utilization_resp(
            instance_id=instance_id,
            start_ts=start_ts,
            end_ts=end_ts,
            period_s=period_s,
        )
        return response.data if isinstance(response.data, list) else []

    def latest_metric_point(
        self,
        *,
        namespace: str,
        metric_name: str,
        dimensions: dict[str, Any] | list[dict[str, Any]] | str,
        start_time: int | str | None = None,
        end_time: int | str | None = None,
        last_minute: int | None = 5,
    ) -> ReturnResponse:
        """Get latest metric point from queried dataset.

        Args:
            namespace: Metric namespace.
            metric_name: Metric name.
            dimensions: Dimension definitions.
            start_time: Optional start time.
            end_time: Optional end time.
            last_minute: Optional rolling window.

        Returns:
            ReturnResponse: ``data`` is ``{"ts": int, "value": float}`` or ``None``.
        """
        response = self.get_metric_data_resp(
            namespace=namespace,
            metric_name=metric_name,
            dimensions=dimensions,
            start_time=start_time,
            end_time=end_time,
            last_minute=last_minute,
        )
        points = response.data if isinstance(response.data, list) else []
        latest_ts: int | None = None
        latest_value: float | None = None

        for point in points:
            if not isinstance(point, dict):
                continue
            ts = self._extract_ts_seconds(point)
            value = self._extract_value(point)
            if ts is None or value is None:
                continue
            if latest_ts is None or ts > latest_ts:
                latest_ts = ts
                latest_value = value

        if latest_ts is None or latest_value is None:
            return ReturnResponse(code=0, msg="success", data=None)
        return ReturnResponse(code=0, msg="success", data={"ts": latest_ts, "value": latest_value})
