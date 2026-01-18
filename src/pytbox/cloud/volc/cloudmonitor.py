from __future__ import annotations

import time
from typing import Any, Dict, Optional

from volcenginesdkvolcobserve.models.dimension_for_get_metric_data_input import (
    DimensionForGetMetricDataInput,
)
from volcenginesdkvolcobserve.models.instance_for_get_metric_data_input import (
    InstanceForGetMetricDataInput,
)
from volcenginesdkvolcobserve.models.get_metric_data_request import GetMetricDataRequest

from ...utils.response import ReturnResponse


class CloudMonitorResource:
    """
    用 volcobserve 的 GetMetricDataRequest 实现云监控查询：
      - instances: [InstanceForGetMetricDataInput(dimensions=[Dimension...])]
      - metric_name / namespace / sub_namespace
      - start_time / end_time
    """

    def __init__(self, client):
        self._c = client
        self._api = self._c.volc_observe_api()

    def get_metric_data(
        self,
        *,
        region: Optional[str] = None,
        dimensions: Dict[str, str] | None = None,
        metric_name: str,
        namespace: str,
        sub_namespace: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        last_minute: int = 5,
    ) -> ReturnResponse:
        """
        查询监控数据（GetMetricData）
        https://console.volcengine.com/cloud_monitor/docs?namespace=VCM_ECS

        - dimensions: dict 形式，例如 {"InstanceId": "i-xxx"}（按文档要求的 key）
        - start_time/end_time: 秒级时间戳；不传则用 last_minute 生成
        """
        # region 覆盖（和 ecs.list 一样逻辑）
        if region:
            self._c.set_region(region)

        now = int(time.time())
        if end_time is None:
            end_time = now
        if start_time is None:
            start_time = end_time - last_minute * 60

        # 构造 instances/dimensions（这是你参考代码里最关键的部分）
        dims = []
        for k, v in (dimensions or {}).items():
            dims.append(DimensionForGetMetricDataInput(name=k, value=v))

        inst = InstanceForGetMetricDataInput(dimensions=dims)

        req = GetMetricDataRequest(
            instances=[inst],
            metric_name=metric_name,
            namespace=namespace,
            sub_namespace=sub_namespace,
            start_time=start_time,
            end_time=end_time,
        )

        resp = self._c.call("volcobserve_get_metric_data", lambda: self._api.get_metric_data(req))

        # SDK response 通常有 to_dict()
        if hasattr(resp, "to_dict"):
            try:
                return ReturnResponse(code=0, msg='success', data=resp.to_dict()['data'])
            except Exception as e:
                return ReturnResponse(code=1, msg=f'error: {e}', data=None)
