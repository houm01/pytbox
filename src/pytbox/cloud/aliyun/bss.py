"""Aliyun BSS resource operations."""

from __future__ import annotations

from typing import Any

from alibabacloud_bssopenapi20171214 import models as bss_models
from alibabacloud_tea_util import models as util_models

from ...schemas.response import ReturnResponse
from ._helpers import body_to_map, extract_total, failure_response


class BSSResource:
    """Aliyun BSS read-only resource wrapper."""

    def __init__(self, client: Any) -> None:
        """Initialize resource.

        Args:
            client: AliyunClient instance.
        """
        self._c = client

    def query_resource_package_instances(
        self,
        *,
        product_code: str,
        page_size: int = 50,
        **kwargs: Any,
    ) -> ReturnResponse:
        """Query resource package instances.

        Args:
            product_code: Aliyun product code, such as ``ossbag``.
            page_size: Number of records per page.
            **kwargs: Additional SDK request arguments.

        Returns:
            ReturnResponse: ``data`` is a flattened resource-package list.
        """
        try:
            page_num = 1
            items_all: list[dict[str, Any]] = []
            runtime = util_models.RuntimeOptions()

            while True:
                request = bss_models.QueryResourcePackageInstancesRequest(
                    product_code=product_code,
                    page_num=page_num,
                    page_size=page_size,
                    **kwargs,
                )
                response = self._c.call(
                    "bss_query_resource_package_instances",
                    lambda: self._c.bss.query_resource_package_instances_with_options(request, runtime),
                )
                body_map = body_to_map(response)
                data = body_map.get("Data") or {}
                instances = (data.get("Instances") or {}).get("Instance") or []
                if not isinstance(instances, list):
                    instances = []
                page_items = [item for item in instances if isinstance(item, dict)]
                if not page_items:
                    break
                items_all.extend(page_items)

                total_count = extract_total(data, "TotalCount")
                if total_count is None:
                    total_count = extract_total(body_map, "Total")
                if total_count is not None:
                    if page_num * page_size >= total_count:
                        break
                elif len(page_items) < page_size:
                    break
                page_num += 1

            return ReturnResponse(code=0, msg="success", data=items_all)
        except Exception as error:  # noqa: BLE001
            return failure_response(error)
