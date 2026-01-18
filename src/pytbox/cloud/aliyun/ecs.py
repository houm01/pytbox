
from typing import List, Dict, Any, Optional

from alibabacloud_ecs20140526 import models as ecs_models
from ...utils.response import ReturnResponse


class ECSResource:
    def __init__(self, client):
        self._c = client
        
    def list(
        self,
        *,
        region: Optional[str] = None,
        page_size: int = 50,
        **kwargs,
    ) -> ReturnResponse:
        """
        列出 ECS 实例（原始阿里云字段，dict 化）

        :param region: 可选，覆盖实例化 Aliyun 时的 region
        :param page_size: 单页数量
        :param kwargs: 透传给 DescribeInstances（如 vpc_id、instance_ids、tag 等）
        :return: List[dict]，每个 dict 为一个 Instance 原始字段
        """
        region_id = region or self._c.cfg.region

        page_number = 1
        instances_all: List[Dict[str, Any]] = []

        while True:
            req = ecs_models.DescribeInstancesRequest(
                region_id=region_id,
                page_size=page_size,
                page_number=page_number,
                **kwargs,
            )

            resp = self._c.call(
                "ecs_list",
                lambda: self._c.ecs.describe_instances(req),
            )

            body = resp.body
            body_map = body.to_map() if hasattr(body, "to_map") else {}

            # 阿里云实例列表路径：Instances.Instance
            instances = (
                body_map.get("Instances", {})
                        .get("Instance", [])
            )

            if instances:
                instances_all.extend(instances)
            else:
                break

            total_count = int(body_map.get("TotalCount", 0) or 0)
            if page_number * page_size >= total_count:
                break
            page_number += 1
        return ReturnResponse(code=0, msg='success', data=instances_all)