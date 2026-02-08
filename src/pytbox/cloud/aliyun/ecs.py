"""Aliyun ECS resource operations."""

from __future__ import annotations

import json
from typing import Any

from alibabacloud_ecs20140526 import models as ecs_models

from ...schemas.response import ReturnResponse


class ECSResource:
    """Aliyun ECS read-only resource wrapper."""

    def __init__(self, client: Any) -> None:
        """Initialize ECS resource.

        Args:
            client: AliyunClient instance.
        """
        self._c = client

    @staticmethod
    def _extract_instances(body_map: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract ECS instances from SDK map.

        Args:
            body_map: SDK response body map.

        Returns:
            list[dict[str, Any]]: Instance list.
        """
        instances = body_map.get("Instances", {}).get("Instance", [])
        if isinstance(instances, list):
            return instances
        return []

    def list(
        self,
        *,
        region: str | None = None,
        page_size: int = 50,
        **kwargs: Any,
    ) -> ReturnResponse:
        """List ECS instances.

        Args:
            region: Optional region override.
            page_size: Number of instances per page.
            **kwargs: Pass-through params for ``DescribeInstancesRequest``.

        Returns:
            ReturnResponse: ``data`` is list of instance dicts.
        """
        region_id = region or self._c.cfg.region
        page_number = 1
        instances_all: list[dict[str, Any]] = []

        while True:
            req = ecs_models.DescribeInstancesRequest(
                region_id=region_id,
                page_size=page_size,
                page_number=page_number,
                **kwargs,
            )
            resp = self._c.call("ecs_list", lambda: self._c.ecs.describe_instances(req))
            body = getattr(resp, "body", None)
            body_map = body.to_map() if hasattr(body, "to_map") else {}

            instances = self._extract_instances(body_map)
            if not instances:
                break
            instances_all.extend(instances)

            total_count = int(body_map.get("TotalCount", 0) or 0)
            if page_number * page_size >= total_count:
                break
            page_number += 1
        return ReturnResponse(code=0, msg="success", data=instances_all)

    def get_instance(
        self,
        instance_id: str,
        *,
        region: str | None = None,
        **kwargs: Any,
    ) -> ReturnResponse:
        """Get a single ECS instance by id.

        Args:
            instance_id: ECS instance id.
            region: Optional region override.
            **kwargs: Additional request parameters.

        Returns:
            ReturnResponse: ``data`` is instance dict or ``None`` when missing.
        """
        region_id = region or self._c.cfg.region
        request_kwargs = dict(kwargs)
        request_kwargs.setdefault("instance_ids", json.dumps([instance_id]))
        req = ecs_models.DescribeInstancesRequest(
            region_id=region_id,
            page_size=1,
            page_number=1,
            **request_kwargs,
        )
        resp = self._c.call("ecs_get_instance", lambda: self._c.ecs.describe_instances(req))
        body = getattr(resp, "body", None)
        body_map = body.to_map() if hasattr(body, "to_map") else {}
        instances = self._extract_instances(body_map)
        return ReturnResponse(code=0, msg="success", data=instances[0] if instances else None)

    def list_instance_ids(self, *, region: str | None = None, **kwargs: Any) -> ReturnResponse:
        """List ECS instance ids.

        Args:
            region: Optional region override.
            **kwargs: Additional list filters.

        Returns:
            ReturnResponse: ``data`` is list of instance ids.
        """
        response = self.list(region=region, **kwargs)
        instances = response.data if isinstance(response.data, list) else []
        instance_ids = [str(item.get("InstanceId")) for item in instances if item.get("InstanceId")]
        return ReturnResponse(code=response.code, msg=response.msg, data=instance_ids)
