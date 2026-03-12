"""Aliyun VPC resource operations."""

from __future__ import annotations

from typing import Any

from alibabacloud_tea_util import models as util_models
from alibabacloud_vpc20160428 import models as vpc_models

from ...schemas.response import ReturnResponse
from ._helpers import body_to_map, extract_collection, extract_total, failure_response


class VPCResource:
    """Aliyun VPC read-only resource wrapper."""

    def __init__(self, client: Any) -> None:
        """Initialize resource.

        Args:
            client: AliyunClient instance.
        """
        self._c = client

    def _list_paginated(
        self,
        *,
        action: str,
        request_cls: Any,
        sdk_method_name: str,
        container_key: str,
        item_key: str,
        region: str | None = None,
        page_size: int = 50,
        **kwargs: Any,
    ) -> ReturnResponse:
        """Run a paginated VPC list request and flatten all pages."""
        region_id = region or self._c.cfg.region
        page_number = 1
        items_all: list[dict[str, Any]] = []
        runtime = util_models.RuntimeOptions()

        while True:
            request = request_cls(
                region_id=region_id,
                page_number=page_number,
                page_size=page_size,
                **kwargs,
            )
            response = self._c.call(
                action,
                lambda: getattr(self._c.vpc, sdk_method_name)(request, runtime),
            )
            body_map = body_to_map(response)
            items = extract_collection(
                body_map,
                container_key=container_key,
                item_key=item_key,
            )
            if not items:
                break
            items_all.extend(items)

            total_count = extract_total(body_map, "TotalCount")
            if total_count is not None:
                if page_number * page_size >= total_count:
                    break
            elif len(items) < page_size:
                break
            page_number += 1

        return ReturnResponse(code=0, msg="success", data=items_all)

    def list_eips(self, *, region: str | None = None, page_size: int = 50, **kwargs: Any) -> ReturnResponse:
        """List EIP addresses."""
        try:
            return self._list_paginated(
                action="vpc_list_eips",
                request_cls=vpc_models.DescribeEipAddressesRequest,
                sdk_method_name="describe_eip_addresses_with_options",
                container_key="EipAddresses",
                item_key="EipAddress",
                region=region,
                page_size=page_size,
                **kwargs,
            )
        except Exception as error:  # noqa: BLE001
            return failure_response(error)

    def list_vpcs(self, *, region: str | None = None, page_size: int = 50, **kwargs: Any) -> ReturnResponse:
        """List VPCs."""
        try:
            return self._list_paginated(
                action="vpc_list_vpcs",
                request_cls=vpc_models.DescribeVpcsRequest,
                sdk_method_name="describe_vpcs_with_options",
                container_key="Vpcs",
                item_key="Vpc",
                region=region,
                page_size=page_size,
                **kwargs,
            )
        except Exception as error:  # noqa: BLE001
            return failure_response(error)

    def list_vswitches(
        self,
        *,
        region: str | None = None,
        page_size: int = 50,
        **kwargs: Any,
    ) -> ReturnResponse:
        """List VSwitches."""
        try:
            return self._list_paginated(
                action="vpc_list_vswitches",
                request_cls=vpc_models.DescribeVSwitchesRequest,
                sdk_method_name="describe_vswitches_with_options",
                container_key="VSwitches",
                item_key="VSwitch",
                region=region,
                page_size=page_size,
                **kwargs,
            )
        except Exception as error:  # noqa: BLE001
            return failure_response(error)

    def list_nat_gateways(
        self,
        *,
        region: str | None = None,
        page_size: int = 50,
        **kwargs: Any,
    ) -> ReturnResponse:
        """List NAT gateways."""
        try:
            return self._list_paginated(
                action="vpc_list_nat_gateways",
                request_cls=vpc_models.DescribeNatGatewaysRequest,
                sdk_method_name="describe_nat_gateways_with_options",
                container_key="NatGateways",
                item_key="NatGateway",
                region=region,
                page_size=page_size,
                **kwargs,
            )
        except Exception as error:  # noqa: BLE001
            return failure_response(error)
