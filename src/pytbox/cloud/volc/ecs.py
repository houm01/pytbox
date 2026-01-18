from typing import Any, Dict, List, Optional

import volcenginesdkecs  # 来自 volcengine-python-sdk :contentReference[oaicite:5]{index=5}
from ...utils.response import ReturnResponse


class ECSResource:
    def __init__(self, client):
        self._c = client
        self._api = self._c.ecs_api()

    def list(
        self,
        *,
        region: Optional[str] = None,
        max_results: int = 100,
        **kwargs,
    ) -> ReturnResponse:
        """
        查询 ECS 实例列表（原样返回：list[dict]）

        规则：
          - region 传了就用传入的
          - 不传就用实例化 Volc 的默认 region

        说明：
          volcengine-python-sdk 的示例里用的是 describe_instances + DescribeInstancesRequest :contentReference[oaicite:6]{index=6}
        """
        # region 覆盖：临时改 configuration.region（只影响这次调用）
        if region:
            self._c.set_region(region)
        else:
            self._c.api_client.configuration.region = self._c.cfg.region  # type: ignore[attr-defined]

        req = volcenginesdkecs.DescribeInstancesRequest(
            max_results=max_results,
            **kwargs,
        )

        resp = self._c.call("ecs_list", lambda: self._api.describe_instances(req))
        data = resp.to_dict()
        return ReturnResponse(code=0, msg='success', data=data['instances'])
