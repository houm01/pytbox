from __future__ import annotations

import time
from typing import Any

from volcenginesdkvolcobserve.models.dimension_for_get_metric_data_input import (
    DimensionForGetMetricDataInput,
)
from volcenginesdkvolcobserve.models.instance_for_get_metric_data_input import (
    InstanceForGetMetricDataInput,
)
from volcenginesdkvolcobserve.models.get_metric_data_request import GetMetricDataRequest

from ...schemas.response import ReturnResponse


class CloudMonitorResource:
    """Volc CloudMonitor read-only resource wrapper."""

    def __init__(self, client: Any) -> None:
        """Initialize resource.

        Args:
            client: VolcClient instance.
        """
        self._c = client
        self._api = self._c.volc_observe_api()

    @staticmethod
    def _extract_points(payload: Any) -> list[dict[str, Any]]:
        """Extract metric points from flexible response payload.

        Args:
            payload: Response payload under ``data``.

        Returns:
            list[dict[str, Any]]: Flattened datapoint list.
        """
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []

        points: list[dict[str, Any]] = []
        for key in ("datapoints", "points", "data"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                points.extend([item for item in candidate if isinstance(item, dict)])

        for key in ("metric_data_results", "results"):
            result_list = payload.get(key)
            if not isinstance(result_list, list):
                continue
            for result in result_list:
                if not isinstance(result, dict):
                    continue
                candidate = result.get("datapoints") or result.get("points")
                if isinstance(candidate, list):
                    points.extend([item for item in candidate if isinstance(item, dict)])
        return points

    @staticmethod
    def _extract_ts_seconds(point: dict[str, Any]) -> int | None:
        """Extract timestamp in seconds.

        Args:
            point: Metric point object.

        Returns:
            int | None: Timestamp in seconds.
        """
        for key in ("timestamp", "Timestamp", "time", "ts"):
            raw_ts = point.get(key)
            if raw_ts is None:
                continue
            try:
                ts = int(raw_ts)
            except (TypeError, ValueError):
                return None
            if ts > 10_000_000_000:
                return ts // 1000
            return ts
        return None

    @staticmethod
    def _extract_value(point: dict[str, Any]) -> float | None:
        """Extract numeric value from metric point.

        Args:
            point: Metric point object.

        Returns:
            float | None: Parsed value.
        """
        for key in ("value", "Value", "avg", "Average", "max", "maximum"):
            raw_value = point.get(key)
            if raw_value is None:
                continue
            try:
                return float(raw_value)
            except (TypeError, ValueError):
                return None
        return None

    def get_metric_data(
        self,
        *,
        region: str | None = None,
        dimensions: dict[str, str] | None = None,
        metric_name: str,
        namespace: str,
        sub_namespace: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        last_minute: int = 5,
    ) -> ReturnResponse:
        """Get CloudMonitor metric data.

        Args:
            region: Optional region override.
            dimensions: Metric dimensions, e.g. ``{"ResourceID": "i-xxx"}``.
            metric_name: Metric name.
            namespace: Metric namespace.
            sub_namespace: Optional metric sub namespace.
            start_time: Optional start timestamp in seconds.
            end_time: Optional end timestamp in seconds.
            last_minute: Rolling window size when start/end are absent.

        Returns:
            ReturnResponse: ``data`` keeps upstream payload under ``data`` field.
        """
        try:
            now = int(time.time())
            if end_time is None:
                end_time = now
            if start_time is None:
                start_time = end_time - (last_minute * 60)

            dim_inputs = [
                DimensionForGetMetricDataInput(name=key, value=value)
                for key, value in (dimensions or {}).items()
            ]
            instance = InstanceForGetMetricDataInput(dimensions=dim_inputs)
            request = GetMetricDataRequest(
                instances=[instance],
                metric_name=metric_name,
                namespace=namespace,
                sub_namespace=sub_namespace,
                start_time=start_time,
                end_time=end_time,
            )

            with self._c.use_region(region):
                response = self._c.call(
                    "volcobserve_get_metric_data",
                    lambda: self._api.get_metric_data(request),
                )

            if hasattr(response, "to_dict"):
                payload = response.to_dict()
                if isinstance(payload, dict):
                    return ReturnResponse(code=0, msg="success", data=payload.get("data", payload))
            if isinstance(response, dict):
                return ReturnResponse(code=0, msg="success", data=response.get("data", response))
            return ReturnResponse(code=0, msg="success", data=response)
        except Exception as error:  # noqa: BLE001
            return ReturnResponse(code=1, msg=f"failed: {error}", data=None)

    def latest_metric_point(
        self,
        *,
        region: str | None = None,
        dimensions: dict[str, str] | None = None,
        metric_name: str,
        namespace: str,
        sub_namespace: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        last_minute: int = 5,
    ) -> ReturnResponse:
        """Get latest point from CloudMonitor metric data.

        Args:
            region: Optional region override.
            dimensions: Metric dimensions.
            metric_name: Metric name.
            namespace: Metric namespace.
            sub_namespace: Optional metric sub namespace.
            start_time: Optional start timestamp in seconds.
            end_time: Optional end timestamp in seconds.
            last_minute: Rolling window size when start/end are absent.

        Returns:
            ReturnResponse: ``data`` is ``{"ts": int, "value": float}`` or ``None``.
        """
        response = self.get_metric_data(
            region=region,
            dimensions=dimensions,
            metric_name=metric_name,
            namespace=namespace,
            sub_namespace=sub_namespace,
            start_time=start_time,
            end_time=end_time,
            last_minute=last_minute,
        )
        if response.code != 0:
            return response

        points = self._extract_points(response.data)
        latest_ts: int | None = None
        latest_value: float | None = None
        for point in points:
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
