"""Aliyun RDS resource operations."""

from __future__ import annotations

from typing import Any

from alibabacloud_rds20140815 import models as rds_models
from alibabacloud_tea_util import models as util_models

from ...schemas.response import ReturnResponse
from ._helpers import body_to_map, extract_collection, extract_total, failure_response


class RDSResource:
    """Aliyun RDS read-only resource wrapper."""

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
        """Run a paginated RDS list request and flatten all pages."""
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
                lambda: getattr(self._c.rds, sdk_method_name)(request, runtime),
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

            total_count = extract_total(body_map, "TotalRecordCount", "TotalCount")
            if total_count is not None:
                if page_number * page_size >= total_count:
                    break
            elif len(items) < page_size:
                break
            page_number += 1

        return ReturnResponse(code=0, msg="success", data=items_all)

    def list_instances(
        self,
        *,
        region: str | None = None,
        page_size: int = 50,
        **kwargs: Any,
    ) -> ReturnResponse:
        """List RDS instances."""
        try:
            return self._list_paginated(
                action="rds_list_instances",
                request_cls=rds_models.DescribeDBInstancesRequest,
                sdk_method_name="describe_dbinstances_with_options",
                container_key="Items",
                item_key="DBInstance",
                region=region,
                page_size=page_size,
                **kwargs,
            )
        except Exception as error:  # noqa: BLE001
            return failure_response(error)

    def get_instance(self, instance_id: str, **kwargs: Any) -> ReturnResponse:
        """Get a single RDS instance by id."""
        try:
            request = rds_models.DescribeDBInstanceAttributeRequest(
                dbinstance_id=instance_id,
                **kwargs,
            )
            runtime = util_models.RuntimeOptions()
            response = self._c.call(
                "rds_get_instance",
                lambda: self._c.rds.describe_dbinstance_attribute_with_options(request, runtime),
            )
            body_map = body_to_map(response)
            items = extract_collection(
                body_map,
                container_key="Items",
                item_key="DBInstanceAttribute",
            )
            return ReturnResponse(code=0, msg="success", data=items[0] if items else None)
        except Exception as error:  # noqa: BLE001
            return failure_response(error)

    def list_whitelist_groups(self, instance_id: str, **kwargs: Any) -> ReturnResponse:
        """List whitelist groups for an RDS instance."""
        try:
            request = rds_models.DescribeDBInstanceIPArrayListRequest(
                dbinstance_id=instance_id,
                **kwargs,
            )
            runtime = util_models.RuntimeOptions()
            response = self._c.call(
                "rds_list_whitelist_groups",
                lambda: self._c.rds.describe_dbinstance_iparray_list_with_options(request, runtime),
            )
            body_map = body_to_map(response)
            groups = extract_collection(
                body_map,
                container_key="Items",
                item_key="DBInstanceIPArray",
            )
            return ReturnResponse(code=0, msg="success", data=groups)
        except Exception as error:  # noqa: BLE001
            return failure_response(error)

    def list_parameters(self, instance_id: str, **kwargs: Any) -> ReturnResponse:
        """List running and configured parameters for an RDS instance."""
        try:
            request = rds_models.DescribeParametersRequest(
                dbinstance_id=instance_id,
                **kwargs,
            )
            runtime = util_models.RuntimeOptions()
            response = self._c.call(
                "rds_list_parameters",
                lambda: self._c.rds.describe_parameters_with_options(request, runtime),
            )
            body_map = body_to_map(response)
            data = {
                "engine": body_map.get("Engine"),
                "engine_version": body_map.get("EngineVersion"),
                "param_group_info": body_map.get("ParamGroupInfo"),
                "running_parameters": extract_collection(
                    body_map,
                    container_key="RunningParameters",
                    item_key="DBInstanceParameter",
                ),
                "config_parameters": extract_collection(
                    body_map,
                    container_key="ConfigParameters",
                    item_key="DBInstanceParameter",
                ),
            }
            return ReturnResponse(code=0, msg="success", data=data)
        except Exception as error:  # noqa: BLE001
            return failure_response(error)

    def get_backup_policy(self, instance_id: str, **kwargs: Any) -> ReturnResponse:
        """Get the backup policy for an RDS instance."""
        try:
            request = rds_models.DescribeBackupPolicyRequest(
                dbinstance_id=instance_id,
                **kwargs,
            )
            runtime = util_models.RuntimeOptions()
            response = self._c.call(
                "rds_get_backup_policy",
                lambda: self._c.rds.describe_backup_policy_with_options(request, runtime),
            )
            return ReturnResponse(code=0, msg="success", data=body_to_map(response))
        except Exception as error:  # noqa: BLE001
            return failure_response(error)
