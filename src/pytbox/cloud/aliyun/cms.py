import json
from typing import List

from alibabacloud_cms20190101 import models as cms_models


class CMSResource:
    def __init__(self, client):
        self._c = client

    def cpu_utilization(
        self,
        *,
        instance_id: str,
        start_ts: int,
        end_ts: int,
        period_s: int = 60,
    ) -> List[dict]:
        """
        返回 points: [{ts: unix_s, value: float}, ...]
        """
        start_ms = start_ts * 1000
        end_ms = end_ts * 1000
        dimensions = json.dumps([{"instanceId": instance_id}])

        req = cms_models.DescribeMetricListRequest(
            namespace="acs_ecs_dashboard",
            metric_name="CPUUtilization",
            dimensions=dimensions,
            start_time=start_ms,
            end_time=end_ms,
            period=str(period_s),
        )

        resp = self._c.call("cms_cpu_utilization", lambda: self._c.cms.describe_metric_list(req))
        body = resp.body
        datapoints_raw = getattr(body, "datapoints", None) or "[]"

        try:
            points = json.loads(datapoints_raw)
        except Exception:  # noqa: BLE001
            points = []

        out: List[dict] = []
        for p in points:
            ts_ms = int(p.get("timestamp") or 0)
            val = p.get("Average")
            if val is None:
                val = p.get("Value")
            if val is None:
                continue
            out.append({"ts": ts_ms // 1000, "value": float(val)})

        return out
