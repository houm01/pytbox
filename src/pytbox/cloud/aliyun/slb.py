"""Aliyun SLB resource operations."""

from __future__ import annotations

from typing import Any

from alibabacloud_slb20140515 import models as slb_models
from alibabacloud_tea_util import models as util_models

from ...schemas.response import ReturnResponse
from ._helpers import body_to_map, extract_collection, extract_total, failure_response


class SLBResource:
    """Aliyun SLB read-only resource wrapper."""

    def __init__(self, client: Any) -> None:
        """Initialize resource.

        Args:
            client: AliyunClient instance.
        """
        self._c = client

    def list_load_balancers(
        self,
        *,
        region: str | None = None,
        page_size: int = 50,
        **kwargs: Any,
    ) -> ReturnResponse:
        """List CLB load balancers."""
        try:
            region_id = region or self._c.cfg.region
            page_number = 1
            load_balancers_all: list[dict[str, Any]] = []
            runtime = util_models.RuntimeOptions()

            while True:
                request = slb_models.DescribeLoadBalancersRequest(
                    region_id=region_id,
                    page_number=page_number,
                    page_size=page_size,
                    **kwargs,
                )
                response = self._c.call(
                    "slb_list_load_balancers",
                    lambda: self._c.slb.describe_load_balancers_with_options(request, runtime),
                )
                body_map = body_to_map(response)
                items = extract_collection(
                    body_map,
                    container_key="LoadBalancers",
                    item_key="LoadBalancer",
                )
                if not items:
                    break
                load_balancers_all.extend(items)

                total_count = extract_total(body_map, "TotalCount")
                if total_count is not None:
                    if page_number * page_size >= total_count:
                        break
                elif len(items) < page_size:
                    break
                page_number += 1

            return ReturnResponse(code=0, msg="success", data=load_balancers_all)
        except Exception as error:  # noqa: BLE001
            return failure_response(error)
