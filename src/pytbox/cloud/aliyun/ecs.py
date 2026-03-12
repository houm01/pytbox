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

    @staticmethod
    def _extract_eip_addresses(body_map: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract EIP addresses from SDK map.

        Args:
            body_map: SDK response body map.

        Returns:
            list[dict[str, Any]]: EIP address list.
        """
        eips = body_map.get("EipAddresses", {}).get("EipAddress", [])
        if isinstance(eips, list):
            return eips
        return []

    @staticmethod
    def _extract_disks(body_map: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract disk list from SDK map.

        Args:
            body_map: SDK response body map.

        Returns:
            list[dict[str, Any]]: Disk list.
        """
        disks = body_map.get("Disks", {}).get("Disk", [])
        if isinstance(disks, list):
            return disks
        return []

    @staticmethod
    def _extract_collection(
        body_map: dict[str, Any],
        *,
        container_key: str,
        item_key: str,
    ) -> list[dict[str, Any]]:
        """Extract list items from a nested SDK response body.

        Args:
            body_map: SDK response body map.
            container_key: Top-level collection key.
            item_key: Item list key inside the collection.

        Returns:
            list[dict[str, Any]]: Extracted items.
        """
        container = body_map.get(container_key) or {}
        if not isinstance(container, dict):
            return []
        items = container.get(item_key) or []
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
        return []

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
        """Run a paginated ECS list request and flatten all pages.

        Args:
            action: Action label for logging and exception mapping.
            request_cls: SDK request model class.
            sdk_method_name: ECS SDK method name.
            container_key: Top-level collection key in response body.
            item_key: Item list key inside the collection.
            region: Optional region override.
            page_size: Number of records per page.
            **kwargs: Additional request parameters.

        Returns:
            ReturnResponse: ``data`` is a list of raw resource dicts.
        """
        region_id = region or self._c.cfg.region
        page_number = 1
        items_all: list[dict[str, Any]] = []

        while True:
            req = request_cls(
                region_id=region_id,
                page_size=page_size,
                page_number=page_number,
                **kwargs,
            )
            resp = self._c.call(
                action,
                lambda: getattr(self._c.ecs, sdk_method_name)(req),
            )
            body = getattr(resp, "body", None)
            body_map = body.to_map() if hasattr(body, "to_map") else {}

            items = self._extract_collection(
                body_map,
                container_key=container_key,
                item_key=item_key,
            )
            if not items:
                break
            items_all.extend(items)

            total_count_raw = body_map.get("TotalCount")
            if isinstance(total_count_raw, str) and total_count_raw.isdigit():
                total_count = int(total_count_raw)
            elif isinstance(total_count_raw, int):
                total_count = total_count_raw
            else:
                total_count = None

            if total_count is not None:
                if page_number * page_size >= total_count:
                    break
            elif len(items) < page_size:
                break

            page_number += 1

        return ReturnResponse(code=0, msg="success", data=items_all)

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

    def list_disks(
        self,
        *,
        region: str | None = None,
        page_size: int = 50,
        **kwargs: Any,
    ) -> ReturnResponse:
        """List ECS disks.

        Args:
            region: Optional region override.
            page_size: Number of disks per page.
            **kwargs: Pass-through params for ``DescribeDisksRequest``.

        Returns:
            ReturnResponse: ``data`` is list of disk dicts.
        """
        return self._list_paginated(
            action="ecs_list_disks",
            request_cls=ecs_models.DescribeDisksRequest,
            sdk_method_name="describe_disks",
            container_key="Disks",
            item_key="Disk",
            region=region,
            page_size=page_size,
            **kwargs,
        )

    def get_disk(
        self,
        disk_id: str,
        *,
        region: str | None = None,
        **kwargs: Any,
    ) -> ReturnResponse:
        """Get a single ECS disk by id.

        Args:
            disk_id: Disk id.
            region: Optional region override.
            **kwargs: Additional request parameters.

        Returns:
            ReturnResponse: ``data`` is disk dict or ``None`` when missing.
        """
        request_kwargs = dict(kwargs)
        request_kwargs.setdefault("disk_ids", json.dumps([disk_id]))
        response = self.list_disks(region=region, page_size=1, **request_kwargs)
        disks = response.data if isinstance(response.data, list) else []
        return ReturnResponse(code=response.code, msg=response.msg, data=disks[0] if disks else None)

    def list_snapshots(
        self,
        *,
        region: str | None = None,
        page_size: int = 50,
        **kwargs: Any,
    ) -> ReturnResponse:
        """List ECS snapshots.

        Args:
            region: Optional region override.
            page_size: Number of snapshots per page.
            **kwargs: Pass-through params for ``DescribeSnapshotsRequest``.

        Returns:
            ReturnResponse: ``data`` is list of snapshot dicts.
        """
        return self._list_paginated(
            action="ecs_list_snapshots",
            request_cls=ecs_models.DescribeSnapshotsRequest,
            sdk_method_name="describe_snapshots",
            container_key="Snapshots",
            item_key="Snapshot",
            region=region,
            page_size=page_size,
            **kwargs,
        )

    def list_auto_snapshot_policies(
        self,
        *,
        region: str | None = None,
        page_size: int = 50,
        **kwargs: Any,
    ) -> ReturnResponse:
        """List automatic snapshot policies.

        Args:
            region: Optional region override.
            page_size: Number of policies per page.
            **kwargs: Pass-through params for ``DescribeAutoSnapshotPolicyExRequest``.

        Returns:
            ReturnResponse: ``data`` is list of policy dicts.
        """
        return self._list_paginated(
            action="ecs_list_auto_snapshot_policies",
            request_cls=ecs_models.DescribeAutoSnapshotPolicyExRequest,
            sdk_method_name="describe_auto_snapshot_policy_ex",
            container_key="AutoSnapshotPolicies",
            item_key="AutoSnapshotPolicy",
            region=region,
            page_size=page_size,
            **kwargs,
        )

    def list_auto_snapshot_policy_associations(
        self,
        *,
        region: str | None = None,
        page_size: int = 50,
        **kwargs: Any,
    ) -> ReturnResponse:
        """List automatic snapshot policy associations.

        Args:
            region: Optional region override.
            page_size: Number of associations per page.
            **kwargs: Pass-through params for ``DescribeAutoSnapshotPolicyAssociationsRequest``.

        Returns:
            ReturnResponse: ``data`` is list of association dicts.
        """
        return self._list_paginated(
            action="ecs_list_auto_snapshot_policy_associations",
            request_cls=ecs_models.DescribeAutoSnapshotPolicyAssociationsRequest,
            sdk_method_name="describe_auto_snapshot_policy_associations",
            container_key="AutoSnapshotPolicyAssociations",
            item_key="AutoSnapshotPolicyAssociation",
            region=region,
            page_size=page_size,
            **kwargs,
        )

    def list_security_groups(
        self,
        *,
        region: str | None = None,
        page_size: int = 50,
        **kwargs: Any,
    ) -> ReturnResponse:
        """List security groups.

        Args:
            region: Optional region override.
            page_size: Number of security groups per page.
            **kwargs: Pass-through params for ``DescribeSecurityGroupsRequest``.

        Returns:
            ReturnResponse: ``data`` is list of security group dicts.
        """
        return self._list_paginated(
            action="ecs_list_security_groups",
            request_cls=ecs_models.DescribeSecurityGroupsRequest,
            sdk_method_name="describe_security_groups",
            container_key="SecurityGroups",
            item_key="SecurityGroup",
            region=region,
            page_size=page_size,
            **kwargs,
        )

    def get_security_group_attribute(
        self,
        security_group_id: str,
        *,
        region: str | None = None,
        **kwargs: Any,
    ) -> ReturnResponse:
        """Get security group rule details.

        Args:
            security_group_id: Security group id.
            region: Optional region override.
            **kwargs: Additional request parameters.

        Returns:
            ReturnResponse: ``data`` is security group detail dict.
        """
        region_id = region or self._c.cfg.region
        req = ecs_models.DescribeSecurityGroupAttributeRequest(
            region_id=region_id,
            security_group_id=security_group_id,
            **kwargs,
        )
        resp = self._c.call(
            "ecs_get_security_group_attribute",
            lambda: self._c.ecs.describe_security_group_attribute(req),
        )
        body = getattr(resp, "body", None)
        body_map = body.to_map() if hasattr(body, "to_map") else {}
        return ReturnResponse(code=0, msg="success", data=body_map or None)

    def list_network_interfaces(
        self,
        *,
        region: str | None = None,
        page_size: int = 50,
        **kwargs: Any,
    ) -> ReturnResponse:
        """List ENIs.

        Args:
            region: Optional region override.
            page_size: Number of ENIs per page.
            **kwargs: Pass-through params for ``DescribeNetworkInterfacesRequest``.

        Returns:
            ReturnResponse: ``data`` is list of ENI dicts.
        """
        return self._list_paginated(
            action="ecs_list_network_interfaces",
            request_cls=ecs_models.DescribeNetworkInterfacesRequest,
            sdk_method_name="describe_network_interfaces",
            container_key="NetworkInterfaceSets",
            item_key="NetworkInterfaceSet",
            region=region,
            page_size=page_size,
            **kwargs,
        )

    def list_instances_full_status(
        self,
        *,
        region: str | None = None,
        page_size: int = 50,
        **kwargs: Any,
    ) -> ReturnResponse:
        """List ECS instance full status records.

        Args:
            region: Optional region override.
            page_size: Number of records per page.
            **kwargs: Pass-through params for ``DescribeInstancesFullStatusRequest``.

        Returns:
            ReturnResponse: ``data`` is list of full status dicts.
        """
        return self._list_paginated(
            action="ecs_list_instances_full_status",
            request_cls=ecs_models.DescribeInstancesFullStatusRequest,
            sdk_method_name="describe_instances_full_status",
            container_key="InstanceFullStatusSet",
            item_key="InstanceFullStatusType",
            region=region,
            page_size=page_size,
            **kwargs,
        )

    def list_instance_history_events(
        self,
        *,
        region: str | None = None,
        page_size: int = 50,
        **kwargs: Any,
    ) -> ReturnResponse:
        """List ECS instance system events.

        Args:
            region: Optional region override.
            page_size: Number of records per page.
            **kwargs: Pass-through params for ``DescribeInstanceHistoryEventsRequest``.

        Returns:
            ReturnResponse: ``data`` is list of event dicts.
        """
        return self._list_paginated(
            action="ecs_list_instance_history_events",
            request_cls=ecs_models.DescribeInstanceHistoryEventsRequest,
            sdk_method_name="describe_instance_history_events",
            container_key="InstanceSystemEventSet",
            item_key="InstanceSystemEventType",
            region=region,
            page_size=page_size,
            **kwargs,
        )

    def list_cloud_assistant_status(
        self,
        *,
        region: str | None = None,
        page_size: int = 50,
        **kwargs: Any,
    ) -> ReturnResponse:
        """List Cloud Assistant agent status.

        Args:
            region: Optional region override.
            page_size: Number of records per page.
            **kwargs: Pass-through params for ``DescribeCloudAssistantStatusRequest``.

        Returns:
            ReturnResponse: ``data`` is list of agent status dicts.
        """
        return self._list_paginated(
            action="ecs_list_cloud_assistant_status",
            request_cls=ecs_models.DescribeCloudAssistantStatusRequest,
            sdk_method_name="describe_cloud_assistant_status",
            container_key="InstanceCloudAssistantStatusSet",
            item_key="InstanceCloudAssistantStatus",
            region=region,
            page_size=page_size,
            **kwargs,
        )

    def list_images(
        self,
        *,
        region: str | None = None,
        page_size: int = 50,
        **kwargs: Any,
    ) -> ReturnResponse:
        """List ECS images.

        Args:
            region: Optional region override.
            page_size: Number of images per page.
            **kwargs: Pass-through params for ``DescribeImagesRequest``.

        Returns:
            ReturnResponse: ``data`` is list of image dicts.
        """
        return self._list_paginated(
            action="ecs_list_images",
            request_cls=ecs_models.DescribeImagesRequest,
            sdk_method_name="describe_images",
            container_key="Images",
            item_key="Image",
            region=region,
            page_size=page_size,
            **kwargs,
        )

    def list_key_pairs(
        self,
        *,
        region: str | None = None,
        page_size: int = 50,
        **kwargs: Any,
    ) -> ReturnResponse:
        """List ECS key pairs.

        Args:
            region: Optional region override.
            page_size: Number of key pairs per page.
            **kwargs: Pass-through params for ``DescribeKeyPairsRequest``.

        Returns:
            ReturnResponse: ``data`` is list of key pair dicts.
        """
        return self._list_paginated(
            action="ecs_list_key_pairs",
            request_cls=ecs_models.DescribeKeyPairsRequest,
            sdk_method_name="describe_key_pairs",
            container_key="KeyPairs",
            item_key="KeyPair",
            region=region,
            page_size=page_size,
            **kwargs,
        )

    def count_unassociated_eip_addresses(
        self,
        *,
        region: str | None = None,
        page_size: int = 50,
        status: str = "Available",
        **kwargs: Any,
    ) -> ReturnResponse:
        """Count unassociated EIP addresses.

        Args:
            region: Optional region override.
            page_size: Number of resources per page.
            status: EIP status filter.
            **kwargs: Pass-through params for ``DescribeEipAddressesRequest``.

        Returns:
            ReturnResponse: ``data`` contains ``count``.
        """
        region_id = region or self._c.cfg.region
        page_number = 1
        count = 0
        request_kwargs = dict(kwargs)
        request_kwargs.setdefault("status", status)

        while True:
            req = ecs_models.DescribeEipAddressesRequest(
                region_id=region_id,
                page_size=page_size,
                page_number=page_number,
                **request_kwargs,
            )
            resp = self._c.call(
                "ecs_count_unassociated_eip_addresses",
                lambda: self._c.ecs.describe_eip_addresses(req),
            )
            body = getattr(resp, "body", None)
            body_map = body.to_map() if hasattr(body, "to_map") else {}

            eips = self._extract_eip_addresses(body_map)
            if not eips:
                break

            count += sum(1 for item in eips if isinstance(item, dict) and not item.get("InstanceId"))

            total_count = int(body_map.get("TotalCount", 0) or 0)
            if page_number * page_size >= total_count:
                break
            page_number += 1

        return ReturnResponse(code=0, msg="success", data={"count": count})

    def count_unattached_disks(
        self,
        *,
        region: str | None = None,
        page_size: int = 50,
        status: str = "Available",
        **kwargs: Any,
    ) -> ReturnResponse:
        """Count unattached disks.

        Args:
            region: Optional region override.
            page_size: Number of resources per page.
            status: Disk status filter.
            **kwargs: Pass-through params for ``DescribeDisksRequest``.

        Returns:
            ReturnResponse: ``data`` contains ``count``.
        """
        region_id = region or self._c.cfg.region
        page_number = 1
        count = 0
        request_kwargs = dict(kwargs)
        request_kwargs.setdefault("status", status)

        while True:
            req = ecs_models.DescribeDisksRequest(
                region_id=region_id,
                page_size=page_size,
                page_number=page_number,
                **request_kwargs,
            )
            resp = self._c.call(
                "ecs_count_unattached_disks",
                lambda: self._c.ecs.describe_disks(req),
            )
            body = getattr(resp, "body", None)
            body_map = body.to_map() if hasattr(body, "to_map") else {}

            disks = self._extract_disks(body_map)
            if not disks:
                break

            count += sum(1 for item in disks if isinstance(item, dict) and not item.get("InstanceId"))

            total_count = int(body_map.get("TotalCount", 0) or 0)
            if page_number * page_size >= total_count:
                break
            page_number += 1

        return ReturnResponse(code=0, msg="success", data={"count": count})
