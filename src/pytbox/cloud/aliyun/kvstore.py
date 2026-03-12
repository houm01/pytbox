"""Aliyun KVStore resource operations."""

from __future__ import annotations

import json
from typing import Any

from alibabacloud_r_kvstore20150101 import models as kvstore_models
from alibabacloud_tea_util import models as util_models

from ...schemas.response import ReturnResponse
from ._helpers import body_to_map, extract_collection, extract_total, failure_response


class KVStoreResource:
    """Aliyun KVStore read-only resource wrapper."""

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
        """Run a paginated KVStore list request and flatten all pages."""
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
                lambda: getattr(self._c.kvstore, sdk_method_name)(request, runtime),
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

    def list_instances(
        self,
        *,
        region: str | None = None,
        page_size: int = 50,
        **kwargs: Any,
    ) -> ReturnResponse:
        """List KVStore instances."""
        try:
            return self._list_paginated(
                action="kvstore_list_instances",
                request_cls=kvstore_models.DescribeInstancesRequest,
                sdk_method_name="describe_instances_with_options",
                container_key="Instances",
                item_key="KVStoreInstance",
                region=region,
                page_size=page_size,
                **kwargs,
            )
        except Exception as error:  # noqa: BLE001
            return failure_response(error)

    def get_instance(self, instance_id: str, **kwargs: Any) -> ReturnResponse:
        """Get a single KVStore instance by id."""
        try:
            request = kvstore_models.DescribeInstanceAttributeRequest(
                instance_id=instance_id,
                **kwargs,
            )
            runtime = util_models.RuntimeOptions()
            response = self._c.call(
                "kvstore_get_instance",
                lambda: self._c.kvstore.describe_instance_attribute_with_options(request, runtime),
            )
            body_map = body_to_map(response)
            items = extract_collection(
                body_map,
                container_key="Instances",
                item_key="DBInstanceAttribute",
            )
            return ReturnResponse(code=0, msg="success", data=items[0] if items else None)
        except Exception as error:  # noqa: BLE001
            return failure_response(error)

    def list_security_ips(self, instance_id: str, **kwargs: Any) -> ReturnResponse:
        """List security IP groups for a KVStore instance."""
        try:
            request = kvstore_models.DescribeSecurityIpsRequest(
                instance_id=instance_id,
                **kwargs,
            )
            runtime = util_models.RuntimeOptions()
            response = self._c.call(
                "kvstore_list_security_ips",
                lambda: self._c.kvstore.describe_security_ips_with_options(request, runtime),
            )
            body_map = body_to_map(response)
            groups = extract_collection(
                body_map,
                container_key="SecurityIpGroups",
                item_key="SecurityIpGroup",
            )
            return ReturnResponse(code=0, msg="success", data=groups)
        except Exception as error:  # noqa: BLE001
            return failure_response(error)

    def list_parameters(
        self,
        instance_id: str,
        *,
        region: str | None = None,
        **kwargs: Any,
    ) -> ReturnResponse:
        """List running and configured parameters for a KVStore instance."""
        try:
            request = kvstore_models.DescribeParametersRequest(
                dbinstance_id=instance_id,
                region_id=region or self._c.cfg.region,
                **kwargs,
            )
            runtime = util_models.RuntimeOptions()
            response = self._c.call(
                "kvstore_list_parameters",
                lambda: self._c.kvstore.describe_parameters_with_options(request, runtime),
            )
            body_map = body_to_map(response)
            data = {
                "engine": body_map.get("Engine"),
                "engine_version": body_map.get("EngineVersion"),
                "running_parameters": extract_collection(
                    body_map,
                    container_key="RunningParameters",
                    item_key="Parameter",
                ),
                "config_parameters": extract_collection(
                    body_map,
                    container_key="ConfigParameters",
                    item_key="Parameter",
                ),
            }
            return ReturnResponse(code=0, msg="success", data=data)
        except Exception as error:  # noqa: BLE001
            return failure_response(error)

    def get_backup_policy(self, instance_id: str, **kwargs: Any) -> ReturnResponse:
        """Get the backup policy for a KVStore instance."""
        try:
            request = kvstore_models.DescribeBackupPolicyRequest(
                instance_id=instance_id,
                **kwargs,
            )
            runtime = util_models.RuntimeOptions()
            response = self._c.call(
                "kvstore_get_backup_policy",
                lambda: self._c.kvstore.describe_backup_policy_with_options(request, runtime),
            )
            return ReturnResponse(code=0, msg="success", data=body_to_map(response))
        except Exception as error:  # noqa: BLE001
            return failure_response(error)
