import json
import time
from typing import List
from datetime import datetime
import pytz
from alibabacloud_cms20190101 import models as cms_models
from alibabacloud_tea_util import models as util_models
from ...utils.response import ReturnResponse


class CMSResource:
    def __init__(self, client):
        self._c = client

    def get_metric_data(
        self,
        *,
        namespace: str,
        metric_name: str,
        dimensions: dict | list[dict] | str,
        start_time: int | None = None,
        end_time: int | None = None,
        last_minute: int | None = None,
    ) -> ReturnResponse:
        """
        获取监控数据

        参数优先级：
        - 如果提供 last_minute，则自动计算时间窗口为 [now - last_minute, now]
        - 否则使用传入的 start_time 和 end_time（单位：秒）
        """
        # 规范化 dimensions：支持 dict / list[dict] / str
        if isinstance(dimensions, str):
            dimensions_str = dimensions
        elif isinstance(dimensions, dict):
            dimensions_str = json.dumps([dimensions])
        elif isinstance(dimensions, list):
            dimensions_str = json.dumps(dimensions)
        else:
            raise TypeError("dimensions 必须是 dict、list[dict] 或 str")

        # 计算时间窗口
        if last_minute is not None:
            now_s = int(time.time())
            start_s = now_s - last_minute * 60
            end_s = now_s
            # 阿里云 API 期望的为 "yyyy-MM-dd HH:mm:ss" (Asia/Shanghai)
   

            tz = pytz.timezone("Asia/Shanghai")

            def to_str(ts):
                return datetime.fromtimestamp(ts, tz).strftime("%Y-%m-%d %H:%M:%S")

            start_str = to_str(start_s)
            end_str = to_str(end_s)
        else:
            if start_time is None or end_time is None:
                raise ValueError(
                    "last_minute 或 start_time+end_time 需二选一提供"
                )
            start_str = start_time
            end_str = end_time

        req = cms_models.DescribeMetricLastRequest(
            namespace=namespace,
            metric_name=metric_name,
            dimensions=dimensions_str,
            start_time=start_str,
            end_time=end_str,
        )

        resp = self._c.call(
            "cms_get_metric_data",
            lambda: self._c.cms.describe_metric_last_with_options(req, runtime=util_models.RuntimeOptions()),
        )
        body = resp.body
        datapoints_raw = getattr(body, "datapoints", None) or "[]"
        try:
            points = json.loads(datapoints_raw)
        except Exception:  # noqa: BLE001
            points = []
        return points

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

        resp = self._c.call(
            "cms_cpu_utilization",
            lambda: self._c.cms.describe_metric_list(req),
        )
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
