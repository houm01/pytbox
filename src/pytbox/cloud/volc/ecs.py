"""Volc ECS resource operations."""

from __future__ import annotations

from typing import Any

import volcenginesdkecs

from ...schemas.response import ReturnResponse


class ECSResource:
    """Volc ECS read-only resource wrapper."""

    def __init__(self, client: Any) -> None:
        """Initialize resource.

        Args:
            client: VolcClient instance.
        """
        self._c = client
        self._api = self._c.ecs_api()

    @staticmethod
    def _response_to_dict(response: Any) -> dict[str, Any]:
        """Convert SDK response to dict safely.

        Args:
            response: SDK response object.

        Returns:
            dict[str, Any]: Response dictionary.
        """
        if hasattr(response, "to_dict"):
            data = response.to_dict()
            return data if isinstance(data, dict) else {}
        if isinstance(response, dict):
            return response
        return {}

    @staticmethod
    def _extract_instances(data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract ECS instances from variable SDK payload shapes.

        Args:
            data: SDK response dictionary.

        Returns:
            list[dict[str, Any]]: Instance list.
        """
        candidates = [
            data.get("instances"),
            data.get("Instances"),
            (data.get("data") or {}).get("instances") if isinstance(data.get("data"), dict) else None,
            (data.get("result") or {}).get("instances") if isinstance(data.get("result"), dict) else None,
        ]
        for candidate in candidates:
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
        return []

    def list(
        self,
        *,
        region: str | None = None,
        max_results: int = 100,
        **kwargs: Any,
    ) -> ReturnResponse:
        """List ECS instances.

        Args:
            region: Optional region override.
            max_results: Maximum result count.
            **kwargs: Additional request parameters.

        Returns:
            ReturnResponse: ``data`` is list of instance dicts.
        """
        with self._c.use_region(region):
            request = volcenginesdkecs.DescribeInstancesRequest(max_results=max_results, **kwargs)
            response = self._c.call("ecs_list", lambda: self._api.describe_instances(request))
        data = self._response_to_dict(response)
        instances = self._extract_instances(data)
        return ReturnResponse(code=0, msg="success", data=instances)

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
            ReturnResponse: ``data`` is instance dict or ``None``.
        """
        request_kwargs = dict(kwargs)
        request_kwargs.setdefault("instance_ids", [instance_id])
        response = self.list(region=region, max_results=1, **request_kwargs)
        instances = response.data if isinstance(response.data, list) else []
        return ReturnResponse(code=response.code, msg=response.msg, data=instances[0] if instances else None)

    def list_instance_ids(self, *, region: str | None = None, **kwargs: Any) -> ReturnResponse:
        """List ECS instance ids.

        Args:
            region: Optional region override.
            **kwargs: Additional list filters.

        Returns:
            ReturnResponse: ``data`` is list of ids.
        """
        response = self.list(region=region, **kwargs)
        instances = response.data if isinstance(response.data, list) else []
        instance_ids: list[str] = []
        for item in instances:
            if not isinstance(item, dict):
                continue
            value = item.get("instance_id") or item.get("InstanceId") or item.get("id")
            if value:
                instance_ids.append(str(value))
        return ReturnResponse(code=response.code, msg=response.msg, data=instance_ids)
