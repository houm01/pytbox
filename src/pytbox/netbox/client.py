#!/usr/bin/env python3

"""NetBox client with unified ReturnResponse contract."""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Literal, Optional, Set, Tuple

import pynetbox
import requests
from pypinyin import lazy_pinyin
from requests import Response
from requests.exceptions import RequestException, Timeout

from ..schemas.response import ReturnResponse
from ..utils.parse import Parse


class NetboxClient:
    """Client wrapper for NetBox REST APIs.

    This client keeps public method names stable while unifying all external IO
    methods to the ``ReturnResponse`` contract.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: int = 10,
        max_retries: int = 3,
        retry_backoff_base: float = 0.5,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """Initialize a NetBox client.

        Args:
            url: NetBox base URL.
            token: NetBox API token.
            timeout: HTTP timeout in seconds.
            max_retries: Maximum retry count, capped at 3.
            retry_backoff_base: Base seconds for exponential backoff.
            logger: Optional logger instance.
        """
        self.url = (url or "").rstrip("/")
        self.token = token or ""
        self.timeout = timeout
        self.max_retries = min(max(max_retries, 1), 3)
        self.retry_backoff_base = retry_backoff_base
        self.logger = logger or logging.getLogger(__name__)
        self.headers = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
        }
        self._id_lookup_cache: Dict[str, Any] = {}
        self._id_lookup_cache_lock = threading.Lock()
        self.pynetbox = pynetbox.api(self.url, token=self.token) if self.url else None

    def _ok(self, msg: str, data: Any = None) -> ReturnResponse:
        """Build a success response.

        Args:
            msg: Message text.
            data: Optional payload.

        Returns:
            ReturnResponse: Standard success response.
        """
        return ReturnResponse(code=0, msg=msg, data=data)

    def _fail(self, msg: str, data: Any = None, code: int = 1) -> ReturnResponse:
        """Build a failure response.

        Args:
            msg: Error message text.
            data: Optional failure payload.
            code: Business error code.

        Returns:
            ReturnResponse: Standard failure response.
        """
        return ReturnResponse(code=code, msg=msg, data=data)

    def _join_url(self, api_url: str) -> str:
        """Resolve API URL to an absolute URL.

        Args:
            api_url: Relative path or absolute URL.

        Returns:
            str: Absolute URL.
        """
        if api_url.startswith("http://") or api_url.startswith("https://"):
            return api_url
        if not api_url.startswith("/"):
            api_url = f"/{api_url}"
        return f"{self.url}{api_url}"

    def _safe_json(self, response: Response) -> Any:
        """Parse response JSON safely.

        Args:
            response: HTTP response.

        Returns:
            Any: Parsed JSON payload or a text wrapper dict.
        """
        try:
            return response.json()
        except ValueError:
            return {"text": response.text}

    def _is_retryable_status(self, status_code: int) -> bool:
        """Check whether an HTTP status code is retryable.

        Args:
            status_code: HTTP status code.

        Returns:
            bool: Whether retry should be attempted.
        """
        return status_code == 429 or status_code >= 500

    def _log_step(self, task_id: str, target: str, result: str, start_ts: float) -> None:
        """Emit key-step logs for external calls.

        Args:
            task_id: Correlation identifier.
            target: Request target.
            result: Execution result.
            start_ts: Monotonic start timestamp.
        """
        duration_ms = int((time.monotonic() - start_ts) * 1000)
        self.logger.info(
            "task_id=%s target=%s result=%s duration_ms=%s",
            task_id,
            target,
            result,
            duration_ms,
        )

    def _request_with_retry(
        self,
        method: str,
        api_url: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Any = None,
        data: Any = None,
    ) -> ReturnResponse:
        """Send an HTTP request with timeout and retry.

        Args:
            method: HTTP method.
            api_url: Relative path or absolute URL.
            params: Optional query params.
            json_data: Optional JSON payload.
            data: Optional raw body payload.

        Returns:
            ReturnResponse: Wrapped HTTP result.
        """
        if not self.url and not api_url.startswith("http"):
            return self._fail("netbox url is not configured")

        full_url = self._join_url(api_url)
        method_upper = method.upper()

        for attempt in range(1, self.max_retries + 1):
            task_id = uuid.uuid4().hex[:8]
            start_ts = time.monotonic()
            try:
                response = requests.request(
                    method=method_upper,
                    url=full_url,
                    headers=self.headers,
                    params=params,
                    json=json_data,
                    data=data,
                    timeout=self.timeout,
                )
                payload = self._safe_json(response)

                if 200 <= response.status_code < 300:
                    self._log_step(task_id, api_url, "ok", start_ts)
                    return self._ok(
                        msg=f"{method_upper} {api_url} success",
                        data=payload,
                    )

                should_retry = (
                    self._is_retryable_status(response.status_code)
                    and attempt < self.max_retries
                )
                self._log_step(task_id, api_url, "retry" if should_retry else "fail", start_ts)

                if should_retry:
                    time.sleep(self.retry_backoff_base * (2 ** (attempt - 1)))
                    continue

                return self._fail(
                    msg=f"{method_upper} {api_url} failed",
                    data={
                        "http_status": response.status_code,
                        "err": payload,
                        "attempt": attempt,
                    },
                )
            except (Timeout, RequestException) as exc:
                should_retry = attempt < self.max_retries
                self._log_step(task_id, api_url, "retry" if should_retry else "fail", start_ts)
                if should_retry:
                    time.sleep(self.retry_backoff_base * (2 ** (attempt - 1)))
                    continue
                return self._fail(
                    msg=f"{method_upper} {api_url} exception",
                    data={"err": str(exc), "attempt": attempt},
                )

        return self._fail(msg=f"{method_upper} {api_url} exhausted retries")

    def _extract_results(self, payload: Any) -> List[Dict[str, Any]]:
        """Extract ``results`` list from a paginated payload.

        Args:
            payload: JSON payload.

        Returns:
            list[dict[str, Any]]: Results list.
        """
        if isinstance(payload, dict):
            results = payload.get("results")
            if isinstance(results, list):
                return [item for item in results if isinstance(item, dict)]
        return []

    def _extract_count(self, payload: Any, results: List[Dict[str, Any]]) -> int:
        """Extract the count from payload.

        Args:
            payload: JSON payload.
            results: Parsed results list.

        Returns:
            int: Result count.
        """
        if isinstance(payload, dict) and isinstance(payload.get("count"), int):
            return payload["count"]
        return len(results)

    def _build_lookup_cache_key(self, api_url: str, params: Dict[str, Any]) -> str:
        """Build a cache key for single-ID lookups.

        Args:
            api_url: API endpoint path.
            params: Query parameters.

        Returns:
            str: Stable cache key.
        """
        serialized_params = json.dumps(params, sort_keys=True, ensure_ascii=False, default=str)
        return f"{api_url}?{serialized_params}"

    def _query_single_id(
        self,
        api_url: str,
        params: Dict[str, Any],
        resource_name: str,
    ) -> ReturnResponse:
        """Query a single object ID by filters.

        Args:
            api_url: API endpoint path.
            params: Query filters.
            resource_name: Resource name for messages.

        Returns:
            ReturnResponse: ``data`` contains object ID or ``None``.
        """
        cleaned_params = Parse.remove_dict_none_value(params)
        if not cleaned_params:
            return self._ok(msg=f"{resource_name} not found", data=None)

        cache_key = self._build_lookup_cache_key(api_url=api_url, params=cleaned_params)
        with self._id_lookup_cache_lock:
            cached_id = self._id_lookup_cache.get(cache_key)
        if cached_id is not None:
            return self._ok(msg=f"{resource_name} found", data=cached_id)

        response = self._request_with_retry("GET", api_url, params=cleaned_params)
        if response.code != 0:
            return response

        results = self._extract_results(response.data)
        count = self._extract_count(response.data, results)
        if count > 1:
            return self._fail(
                msg=f"{resource_name} has multiple results",
                data={"params": cleaned_params, "count": count},
            )
        if count == 0:
            return self._ok(msg=f"{resource_name} not found", data=None)
        resolved_id = results[0].get("id")
        if resolved_id is not None:
            with self._id_lookup_cache_lock:
                self._id_lookup_cache[cache_key] = resolved_id
        return self._ok(msg=f"{resource_name} found", data=resolved_id)

    def _upsert_resource(
        self,
        api_url: str,
        resource_id: Optional[Any],
        payload: Dict[str, Any],
        resource_name: str,
        resource_key: str,
    ) -> ReturnResponse:
        """Create or update a NetBox resource.

        Args:
            api_url: API endpoint path.
            resource_id: Existing resource ID.
            payload: Request payload.
            resource_name: Resource label.
            resource_key: Resource key text for logs/messages.

        Returns:
            ReturnResponse: Upsert execution result.
        """
        method = "PUT" if resource_id else "POST"
        target_api = f"{api_url}{resource_id}/" if resource_id else api_url
        action = "updated" if resource_id else "created"

        response = self._request_with_retry(method, target_api, json_data=payload)
        if response.code != 0:
            return self._fail(
                msg=f"{resource_name} [{resource_key}] {action} failed",
                data=response.data,
            )
        return self._ok(
            msg=f"{resource_name} [{resource_key}] {action} successfully",
            data=response.data,
        )

    def _run_parallel_batch(
        self,
        target: str,
        items: List[Dict[str, Any]],
        dedupe_key_getter: Callable[[Dict[str, Any]], str],
        worker: Callable[[Dict[str, Any]], ReturnResponse],
        max_workers: int,
    ) -> ReturnResponse:
        """Run batch tasks in parallel and aggregate outcomes.

        Args:
            target: Batch target for logging.
            items: Batch input items.
            dedupe_key_getter: Function producing a uniqueness key per item.
            worker: Per-item executor.
            max_workers: Maximum worker threads.

        Returns:
            ReturnResponse: Aggregated execution result.
        """
        if max_workers < 1:
            return self._fail(msg="max_workers must be >= 1")

        batch_task_id = uuid.uuid4().hex[:8]
        start_ts = time.monotonic()
        seen_keys: Set[str] = set()
        indexed_work_items: List[Tuple[int, str, Dict[str, Any]]] = []
        indexed_results: Dict[int, Dict[str, Any]] = {}

        for index, item in enumerate(items):
            try:
                item_key = dedupe_key_getter(item)
            except Exception as exc:
                indexed_results[index] = {
                    "index": index,
                    "key": f"index:{index}",
                    "code": 1,
                    "msg": f"{target} item key error",
                    "data": {"item": item, "err": str(exc)},
                }
                continue
            if item_key in seen_keys:
                indexed_results[index] = {
                    "index": index,
                    "key": item_key,
                    "code": 1,
                    "msg": f"{target} duplicate item",
                    "data": {"item": item},
                }
                continue
            seen_keys.add(item_key)
            indexed_work_items.append((index, item_key, item))

        worker_count = min(max_workers, len(indexed_work_items))
        if worker_count > 0:
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                future_to_item = {
                    executor.submit(worker, item): (index, item_key, item)
                    for index, item_key, item in indexed_work_items
                }
                for future in as_completed(future_to_item):
                    index, item_key, item = future_to_item[future]
                    try:
                        response = future.result()
                    except Exception as exc:  # pragma: no cover - safety fallback
                        response = self._fail(
                            msg=f"{target} item exception",
                            data={"err": str(exc), "item": item},
                        )
                    indexed_results[index] = {
                        "index": index,
                        "key": item_key,
                        "code": response.code,
                        "msg": response.msg,
                        "data": response.data,
                    }

        ordered_results = [indexed_results[index] for index in sorted(indexed_results)]
        success_count = sum(1 for result in ordered_results if result["code"] == 0)
        failed_count = len(ordered_results) - success_count
        summary = {
            "total": len(items),
            "success": success_count,
            "failed": failed_count,
            "results": ordered_results,
        }

        batch_result = "ok" if failed_count == 0 else "partial_fail"
        self._log_step(batch_task_id, target, batch_result, start_ts)
        if failed_count > 0:
            return self._fail(msg=f"{target} completed with failures", data=summary)
        return self._ok(msg=f"{target} completed", data=summary)

    def get_update_comments(self, source: str = "") -> str:
        """Generate update comment text.

        Args:
            source: Source marker.

        Returns:
            str: Formatted comment text.
        """
        return (
            "Updated by automation script\n"
            f"Date: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n"
            f"Source: {source}"
        )

    def get_org_sites_regions(self) -> ReturnResponse:
        """Get NetBox regions list.

        Returns:
            ReturnResponse: Regions payload.
        """
        response = self._request_with_retry("GET", "/api/dcim/regions/")
        if response.code != 0:
            return response
        return self._ok(msg="regions fetched", data=response.data)

    def get_region_id(self, name: Optional[str]) -> ReturnResponse:
        """Get region ID by name.

        Args:
            name: Region name.

        Returns:
            ReturnResponse: Region ID in ``data``.
        """
        return self._query_single_id(
            "/api/dcim/regions/",
            {"name": name},
            "region",
        )

    def add_or_update_region(self, name: str, slug: Optional[str] = None) -> ReturnResponse:
        """Create or update a region.

        Args:
            name: Region name.
            slug: Optional region slug.

        Returns:
            ReturnResponse: Upsert result.
        """
        resolved_slug = self._process_slug(name if slug is None else slug)
        payload = Parse.remove_dict_none_value({"name": name, "slug": resolved_slug})
        region_id_response = self.get_region_id(name=name)
        if region_id_response.code != 0:
            return region_id_response

        return self._upsert_resource(
            "/api/dcim/regions/",
            region_id_response.data,
            payload,
            "region",
            name,
        )

    def get_dcim_site_id(self, name: Optional[str]) -> ReturnResponse:
        """Get site ID by name.

        Args:
            name: Site name.

        Returns:
            ReturnResponse: Site ID in ``data``.
        """
        return self.get_site_id(name=name)

    def add_or_update_org_sites_sites(
        self,
        name: str,
        slug: Optional[str] = None,
        status: Literal["planned", "staging", "active", "decommissioning", "retired"] = "active",
        address: str = "",
        region: Optional[str] = None,
        tenant: Optional[str] = None,
        facility: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        time_zone: str = "Asia/Shanghai",
        tags: Optional[dict] = None,
    ) -> ReturnResponse:
        """Create or update a site with extended fields.

        Args:
            name: Site name.
            slug: Site slug.
            status: Site status.
            address: Physical address.
            region: Region name.
            tenant: Tenant name.
            facility: Facility value.
            latitude: Latitude value.
            longitude: Longitude value.
            time_zone: Timezone name.
            tags: Optional tag dict.

        Returns:
            ReturnResponse: Upsert result.
        """
        region_id_response = self.get_region_id(region)
        if region_id_response.code != 0:
            return region_id_response

        tenant_id_response = self.get_tenant_id(tenant)
        if tenant_id_response.code != 0:
            return tenant_id_response

        site_id_response = self.get_site_id(name=name)
        if site_id_response.code != 0:
            return site_id_response

        resolved_slug = self._process_slug(name if slug is None else slug)
        payload = {
            "name": name,
            "slug": resolved_slug,
            "status": status,
            "facility": str(facility) if facility is not None else None,
            "region": region_id_response.data,
            "tenant": tenant_id_response.data,
            "tags": [tags] if tags is not None else None,
            "time_zone": time_zone,
            "physical_address": address,
            "latitude": self._process_gps(latitude),
            "longitude": self._process_gps(longitude),
        }
        payload = Parse.remove_dict_none_value(payload)

        return self._upsert_resource(
            "/api/dcim/sites/",
            site_id_response.data,
            payload,
            "site",
            name,
        )

    def get_dcim_location_id(self, name: Optional[str]) -> ReturnResponse:
        """Get location ID by name.

        Args:
            name: Location name.

        Returns:
            ReturnResponse: Location ID in ``data``.
        """
        return self._query_single_id(
            "/api/dcim/locations/",
            {"name": name},
            "location",
        )

    def add_or_update_dcim_location(
        self,
        name: str,
        slug: Optional[str] = None,
        site_name: Optional[str] = None,
        status: Literal["planned", "staging", "active", "decommissioning", "retired"] = "active",
        parent_name: Optional[str] = None,
    ) -> ReturnResponse:
        """Create or update a dcim location.

        Args:
            name: Location name.
            slug: Location slug.
            site_name: Parent site name.
            status: Location status.
            parent_name: Parent location name.

        Returns:
            ReturnResponse: Upsert result.
        """
        resolved_slug = self._process_slug(name if slug is None else slug)

        site_id_response = self.get_dcim_site_id(name=site_name)
        if site_id_response.code != 0:
            return site_id_response

        parent_id_response = self.get_dcim_location_id(name=parent_name)
        if parent_id_response.code != 0:
            return parent_id_response

        location_id_response = self.get_dcim_location_id(name=name)
        if location_id_response.code != 0:
            return location_id_response

        payload = Parse.remove_dict_none_value(
            {
                "name": name,
                "slug": resolved_slug,
                "site": site_id_response.data,
                "parent": parent_id_response.data,
                "status": status,
            }
        )

        return self._upsert_resource(
            "/api/dcim/locations/",
            location_id_response.data,
            payload,
            "location",
            name,
        )

    def get_ipam_ipaddress_id(self, address: Optional[str]) -> ReturnResponse:
        """Get IP address ID by address.

        Args:
            address: IP address string.

        Returns:
            ReturnResponse: IP address ID in ``data``.
        """
        return self._query_single_id(
            "/api/ipam/ip-addresses/",
            {"address": address},
            "ip-address",
        )

    def get_tenants_id(self, name: Optional[str]) -> ReturnResponse:
        """Get tenant ID by name.

        Args:
            name: Tenant name.

        Returns:
            ReturnResponse: Tenant ID in ``data``.
        """
        return self._query_single_id(
            "/api/tenancy/tenants/",
            {"name": name},
            "tenant",
        )

    def assign_ipaddress_to_interface(
        self,
        address: str,
        device: str,
        interface_name: str,
    ) -> ReturnResponse:
        """Assign an IP address to an interface.

        Args:
            address: IP address.
            device: Device name.
            interface_name: Interface name.

        Returns:
            ReturnResponse: Assignment result.
        """
        interface_id_response = self.get_interface_id(device=device, name=interface_name)
        if interface_id_response.code != 0:
            return interface_id_response

        ip_id_response = self.get_ipam_ipaddress_id(address=address)
        if ip_id_response.code != 0:
            return ip_id_response
        if ip_id_response.data is None:
            return self._fail(msg=f"ip-address [{address}] not found")

        payload = {
            "address": address,
            "assigned_object_type": "dcim.interface",
            "assigned_object_id": interface_id_response.data,
        }

        response = self._request_with_retry(
            "PUT",
            f"/api/ipam/ip-addresses/{ip_id_response.data}/",
            json_data=payload,
        )
        if response.code != 0:
            return self._fail(msg=f"ip-address [{address}] assign failed", data=response.data)
        return self._ok(msg=f"ip-address [{address}] assigned", data=response.data)

    def add_or_update_ipam_ipaddress(
        self,
        address: str,
        status: Literal["active", "reserved", "deprecated", "dhcp", "slaac"] = "active",
        tenant: Optional[str] = None,
        ip_type: Optional[Literal["BGP", "电信", "联通", "移动", "Other"]] = None,
        description: Optional[str] = None,
        assigned_object_type: Optional[Literal["dcim.interface"]] = None,
        assigned_object_id: Optional[int] = None,
    ) -> ReturnResponse:
        """Create or update an IP address.

        Args:
            address: IP address.
            status: IP status.
            tenant: Tenant name.
            ip_type: IP type label.
            description: Description text.
            assigned_object_type: Assigned object type.
            assigned_object_id: Assigned object ID.

        Returns:
            ReturnResponse: Upsert result.
        """
        tenant_id_response = self.get_tenants_id(name=tenant)
        if tenant_id_response.code != 0:
            return tenant_id_response

        payload: Dict[str, Any] = {
            "address": address,
            "tenant": tenant_id_response.data,
            "status": status,
            "description": description,
            "assigned_object_type": assigned_object_type,
            "assigned_object_id": assigned_object_id,
        }

        if ip_type:
            slug_map = {
                "BGP": "bgp",
                "电信": "china_telecom",
                "联通": "china_unicom",
                "移动": "china_mobile",
                "Other": "other",
            }
            payload["tags"] = [{"name": ip_type, "slug": slug_map.get(ip_type, "other")}]

        payload = Parse.remove_dict_none_value(payload)

        ip_id_response = self.get_ipam_ipaddress_id(address=address)
        if ip_id_response.code != 0:
            return ip_id_response

        return self._upsert_resource(
            "/api/ipam/ip-addresses/",
            ip_id_response.data,
            payload,
            "ip-address",
            address,
        )

    def get_ipam_prefix_id(self, prefix: Optional[str]) -> ReturnResponse:
        """Get prefix ID by prefix value.

        Args:
            prefix: Prefix value.

        Returns:
            ReturnResponse: Prefix ID in ``data``.
        """
        return self._query_single_id(
            "/api/ipam/prefixes/",
            {"prefix": prefix},
            "prefix",
        )

    def get_prefix_id_by_prefix(self, prefix: Optional[str]) -> ReturnResponse:
        """Get prefix ID by prefix value.

        Args:
            prefix: Prefix value.

        Returns:
            ReturnResponse: Prefix ID in ``data``.
        """
        return self.get_ipam_prefix_id(prefix=prefix)

    def add_or_update_ipam_prefix(
        self,
        prefix: str,
        status: Literal["active", "reserved", "deprecated", "dhcp", "slaac"] = "active",
        vlan_id: Optional[int] = 1,
        description: Optional[str] = None,
        tenant: Optional[str] = None,
    ) -> ReturnResponse:
        """Create or update a prefix.

        Args:
            prefix: Prefix value.
            status: Prefix status.
            vlan_id: VLAN ID.
            description: Description text.
            tenant: Tenant name.

        Returns:
            ReturnResponse: Upsert result.
        """
        tenant_id_response = self.get_tenants_id(name=tenant)
        if tenant_id_response.code != 0:
            return tenant_id_response

        payload = {
            "prefix": prefix,
            "status": status,
            "description": description,
            "tenant": tenant_id_response.data,
            "vlan": vlan_id,
        }
        payload = Parse.remove_dict_none_value(payload)

        prefix_id_response = self.get_prefix_id_by_prefix(prefix=prefix)
        if prefix_id_response.code != 0:
            return prefix_id_response

        return self._upsert_resource(
            "/api/ipam/prefixes/",
            prefix_id_response.data,
            payload,
            "prefix",
            prefix,
        )

    def get_ipam_ip_range_id(
        self,
        start_address: Optional[str],
        end_address: Optional[str],
    ) -> ReturnResponse:
        """Get IP range ID by start and end addresses.

        Args:
            start_address: Start address.
            end_address: End address.

        Returns:
            ReturnResponse: IP range ID in ``data``.
        """
        return self._query_single_id(
            "/api/ipam/ip-ranges/",
            {"start_address": start_address, "end_address": end_address},
            "ip-range",
        )

    def add_or_update_ip_ranges(
        self,
        start_address: str,
        end_address: str,
        status: Literal["active", "reserved", "deprecated"] = "active",
        description: Optional[str] = None,
        comments: Optional[str] = None,
    ) -> ReturnResponse:
        """Create or update an IP range.

        Args:
            start_address: Start address.
            end_address: End address.
            status: IP range status.
            description: Description text.
            comments: Comments text.

        Returns:
            ReturnResponse: Upsert result.
        """
        range_id_response = self.get_ipam_ip_range_id(start_address=start_address, end_address=end_address)
        if range_id_response.code != 0:
            return range_id_response

        payload = Parse.remove_dict_none_value(
            {
                "start_address": start_address,
                "end_address": end_address,
                "status": status,
                "description": description,
                "comments": comments,
            }
        )

        return self._upsert_resource(
            "/api/ipam/ip-ranges/",
            range_id_response.data,
            payload,
            "ip-range",
            f"{start_address}-{end_address}",
        )

    def add_or_update_tenants(self, name: str, slug: Optional[str] = None) -> ReturnResponse:
        """Create or update a tenant.

        Args:
            name: Tenant name.
            slug: Optional tenant slug.

        Returns:
            ReturnResponse: Upsert result.
        """
        resolved_slug = self._process_slug(name if slug is None else slug)
        tenant_id_response = self.get_tenants_id(name=name)
        if tenant_id_response.code != 0:
            return tenant_id_response

        payload = {"name": name, "slug": resolved_slug}
        return self._upsert_resource(
            "/api/tenancy/tenants/",
            tenant_id_response.data,
            payload,
            "tenant",
            name,
        )

    def _process_slug(self, name: str) -> str:
        """Normalize slug value.

        Args:
            name: Source value.

        Returns:
            str: Normalized slug.
        """
        slug_mapping = {
            "联想": "lenovo",
            "群晖": "synology",
            "锐捷": "ruijie",
            "创旗": "trunkey",
            "创旗 TSDS-600": "trunkey_tsds_600",
            "磁带库": "tape_library",
            "行为管理": "ac",
            "路由器": "router",
            "交换机": "switch",
            "防火墙": "firewall",
            "存储": "storage",
            "其他": "other",
            "打印机": "printer",
            "服务器": "server",
            "无线控制器": "wireless_ac",
            "待补充": "other",
            "备案系统": "icp_system",
            "堡垒机": "bastion_host",
            "负载均衡": "load_balancer",
            "客户": "customer",
            "运维": "devops",
            "供应商": "vendor",
        }
        slug = slug_mapping.get(name)
        if slug is None:
            slug = "".join(lazy_pinyin(name))
        return (
            slug.lower()
            .replace(" ", "_")
            .replace("-", "_")
            .replace("(", "")
            .replace(")", "")
            .replace("（", "")
            .replace("）", "")
            .replace("+", "")
            .replace("’", "")
            .replace("'", "")
        )

    def _process_gps(self, value: Optional[Any]) -> Optional[float]:
        """Normalize GPS value.

        Args:
            value: Raw GPS value.

        Returns:
            Optional[float]: Rounded float GPS value.
        """
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.replace("\u200c\u200c", "").strip()
            if cleaned == "":
                return None
        else:
            cleaned = str(value)
        try:
            return round(float(cleaned), 2)
        except ValueError:
            return None

    def get_manufacturer_id_by_name(self, name: Optional[str]) -> ReturnResponse:
        """Get manufacturer ID by name.

        Args:
            name: Manufacturer name.

        Returns:
            ReturnResponse: Manufacturer ID in ``data``.
        """
        return self._query_single_id(
            "/api/dcim/manufacturers/",
            {"name": name},
            "manufacturer",
        )

    def add_or_update_device_type(
        self,
        model: Literal["ISR1100-4G", "MS210-48FP", "MS210-24FP", "MR44"],
        slug: Optional[str] = None,
        u_height: Optional[int] = None,
        manufacturer: Optional[str] = None,
    ) -> ReturnResponse:
        """Create or update a device type.

        Args:
            model: Device model.
            slug: Optional slug.
            u_height: Device height.
            manufacturer: Manufacturer name.

        Returns:
            ReturnResponse: Upsert result.
        """
        manufacturer_id_response = self.get_manufacturer_id_by_name(name=manufacturer)
        if manufacturer_id_response.code != 0:
            return manufacturer_id_response

        default_u_height = {
            "ISR1100-4G": 1,
            "MS210-48FP": 1,
            "MS210-24FP": 1,
            "MR44": 1,
        }
        resolved_u_height = default_u_height.get(model, 1) if u_height is None else u_height
        resolved_slug = self._process_slug(model if slug is None else slug)

        payload = {
            "model": model,
            "slug": resolved_slug,
            "u_height": resolved_u_height,
            "manufacturer": manufacturer_id_response.data,
        }

        device_type_id_response = self.get_device_type_id(model=model)
        if device_type_id_response.code != 0:
            return device_type_id_response

        return self._upsert_resource(
            "/api/dcim/device-types/",
            device_type_id_response.data,
            payload,
            "device-type",
            model,
        )

    def get_device_type_id(self, model: Optional[str]) -> ReturnResponse:
        """Get device type ID by model.

        Args:
            model: Device model.

        Returns:
            ReturnResponse: Device type ID in ``data``.
        """
        return self._query_single_id(
            "/api/dcim/device-types/",
            {"model": model},
            "device-type",
        )

    def get_manufacturer_id(self, name: Optional[str]) -> ReturnResponse:
        """Get manufacturer ID by name.

        Args:
            name: Manufacturer name.

        Returns:
            ReturnResponse: Manufacturer ID in ``data``.
        """
        return self.get_manufacturer_id_by_name(name=name)

    def add_or_update_manufacturer(
        self,
        name: Literal["Cisco Viptela", "Cisco Meraki", "Cisco", "PaloAlto"],
        slug: Optional[str] = None,
    ) -> ReturnResponse:
        """Create or update a manufacturer.

        Args:
            name: Manufacturer name.
            slug: Optional slug.

        Returns:
            ReturnResponse: Upsert result.
        """
        manufacturer_id_response = self.get_manufacturer_id(name=name)
        if manufacturer_id_response.code != 0:
            return manufacturer_id_response

        resolved_slug = self._process_slug(name if slug is None else slug)
        payload = {"name": name, "slug": resolved_slug}

        return self._upsert_resource(
            "/api/dcim/manufacturers/",
            manufacturer_id_response.data,
            payload,
            "manufacturer",
            name,
        )

    def get_device_id_by_name(self, name: Optional[str]) -> ReturnResponse:
        """Get device ID by device name.

        Args:
            name: Device name.

        Returns:
            ReturnResponse: Device ID in ``data``.
        """
        return self._query_single_id(
            "/api/dcim/devices/",
            {"name": name},
            "device",
        )

    def get_tenant_id(self, name: Optional[str]) -> ReturnResponse:
        """Get tenant ID by tenant name.

        Args:
            name: Tenant name.

        Returns:
            ReturnResponse: Tenant ID in ``data``.
        """
        return self.get_tenants_id(name=name)

    def get_site_id(self, name: Optional[str]) -> ReturnResponse:
        """Get site ID by site name.

        Args:
            name: Site name.

        Returns:
            ReturnResponse: Site ID in ``data``.
        """
        return self._query_single_id(
            "/api/dcim/sites/",
            {"name": name},
            "site",
        )

    def get_device_id(
        self,
        name: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> ReturnResponse:
        """Get device ID by name and tenant.

        Args:
            name: Device name.
            tenant_id: Tenant ID filter.

        Returns:
            ReturnResponse: Device ID in ``data``.
        """
        return self._query_single_id(
            "/api/dcim/devices/",
            {"name": name, "tenant_id": tenant_id},
            "device",
        )

    def get_device_type_id_by_name(self, name: Optional[str]) -> ReturnResponse:
        """Get device type ID by model name with fallback.

        Args:
            name: Device type model name.

        Returns:
            ReturnResponse: Device type ID in ``data``.
        """
        primary_name = name or "other"
        primary_response = self.get_device_type_id(model=primary_name)
        if primary_response.code != 0:
            return primary_response
        if primary_response.data is not None:
            return primary_response
        if primary_name == "other":
            return primary_response
        return self.get_device_type_id(model="other")

    def add_or_update_device(
        self,
        name: str,
        device_type: Literal["ISR1100-4G", "MS210-48FP", "MS210-24FP", "MR44", "MR42", "other"] = "other",
        site: Optional[str] = None,
        status: Literal["active", "offline", "planned", "staged", "failed"] = "active",
        role: Literal["router", "switch", "wireless_ap", "other"] = "other",
        description: Optional[str] = None,
        primary_ip4: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        rack: Optional[str] = None,
        tenant: Optional[str] = None,
        serial: Optional[str] = None,
        face: Literal["front", "rear"] = "front",
        position: Optional[int] = None,
        comments: Optional[str] = None,
        software_version: Optional[str] = None,
    ) -> ReturnResponse:
        """Create or update a device.

        Args:
            name: Device name.
            device_type: Device type.
            site: Site name.
            status: Device status.
            role: Device role name.
            description: Description text.
            primary_ip4: Primary IPv4 value.
            latitude: Latitude value.
            longitude: Longitude value.
            rack: Rack name.
            tenant: Tenant name.
            serial: Serial number.
            face: Rack face.
            position: Rack position.
            comments: Comments text.
            software_version: Software version.

        Returns:
            ReturnResponse: Upsert result.
        """
        device_type_id_response = self.get_device_type_id_by_name(name=device_type)
        if device_type_id_response.code != 0:
            return device_type_id_response

        role_id_response = self.get_device_role_id(name=role)
        if role_id_response.code != 0:
            return role_id_response

        site_id_response = self.get_site_id(name=site)
        if site_id_response.code != 0:
            return site_id_response

        tenant_id_response = self.get_tenant_id(name=tenant)
        if tenant_id_response.code != 0:
            return tenant_id_response

        ip_id_response = self.get_ipam_ipaddress_id(address=primary_ip4)
        if ip_id_response.code != 0:
            return ip_id_response

        rack_id_response = self.get_rack_id(name=rack, tenant=tenant)
        if rack_id_response.code != 0:
            return rack_id_response

        payload: Dict[str, Any] = {
            "name": name,
            "device_type": device_type_id_response.data,
            "role": role_id_response.data,
            "site": site_id_response.data,
            "description": description,
            "status": status,
            "primary_ip4": ip_id_response.data,
            "latitude": self._process_gps(latitude),
            "longitude": self._process_gps(longitude),
            "rack": rack_id_response.data,
            "tenant": tenant_id_response.data,
            "serial": serial,
            "face": face,
            "position": position,
            "comments": comments,
        }

        if software_version:
            payload["custom_fields"] = {"SoftwareVersion": software_version}

        payload = Parse.remove_dict_none_value(payload)

        device_id_response = self.get_device_id(
            name=name,
            tenant_id=tenant_id_response.data,
        )
        if device_id_response.code != 0:
            return device_id_response

        return self._upsert_resource(
            "/api/dcim/devices/",
            device_id_response.data,
            payload,
            "device",
            name,
        )

    def set_primary_ip4_to_device(
        self,
        device_name: str,
        tenant: Optional[str],
        primary_ip4: str,
    ) -> ReturnResponse:
        """Set primary IPv4 for a device.

        Args:
            device_name: Device name.
            tenant: Tenant name.
            primary_ip4: IPv4 value.

        Returns:
            ReturnResponse: Update result.
        """
        tenant_id_response = self.get_tenant_id(name=tenant)
        if tenant_id_response.code != 0:
            return tenant_id_response

        device_id_response = self.get_device_id(
            name=device_name,
            tenant_id=tenant_id_response.data,
        )
        if device_id_response.code != 0:
            return device_id_response
        if device_id_response.data is None:
            return self._fail(msg=f"device [{device_name}] not found")

        ip_id_response = self.get_ipam_ipaddress_id(address=primary_ip4)
        if ip_id_response.code != 0:
            return ip_id_response

        payload = Parse.remove_dict_none_value(
            {
                "name": device_name,
                "tenant": tenant_id_response.data,
                "primary_ip4": ip_id_response.data,
            }
        )

        response = self._request_with_retry(
            "PUT",
            f"/api/dcim/devices/{device_id_response.data}/",
            json_data=payload,
        )
        if response.code != 0:
            return self._fail(msg=f"device [{device_name}] update failed", data=response.data)
        return self._ok(msg=f"device [{device_name}] updated", data=response.data)

    def update_device_fields(
        self,
        name: str,
        fields: Dict[str, Any],
        tenant: Optional[str] = None,
    ) -> ReturnResponse:
        """Update selected fields on a device with PATCH.

        Args:
            name: Device name.
            fields: Fields to patch.
            tenant: Optional tenant name.

        Returns:
            ReturnResponse: Update result.
        """
        if not fields:
            return self._fail(msg=f"device [{name}] fields are required")

        payload = Parse.remove_dict_none_value(fields)
        if not payload:
            return self._fail(msg=f"device [{name}] fields are required")

        tenant_id_response = self.get_tenant_id(name=tenant)
        if tenant_id_response.code != 0:
            return tenant_id_response

        device_id_response = self.get_device_id(
            name=name,
            tenant_id=tenant_id_response.data,
        )
        if device_id_response.code != 0:
            return device_id_response
        if device_id_response.data is None:
            return self._fail(msg=f"device [{name}] not found")

        response = self._request_with_retry(
            "PATCH",
            f"/api/dcim/devices/{device_id_response.data}/",
            json_data=payload,
        )
        if response.code != 0:
            return self._fail(msg=f"device [{name}] patch failed", data=response.data)
        return self._ok(msg=f"device [{name}] patched", data=response.data)

    def bulk_update_device_fields(
        self,
        updates: List[Dict[str, Any]],
        max_workers: int = 5,
    ) -> ReturnResponse:
        """Patch device fields in parallel.

        Args:
            updates: List of update items, each containing ``name``, ``tenant``,
                and ``fields`` keys.
            max_workers: Maximum worker threads.

        Returns:
            ReturnResponse: Aggregated batch result.
        """

        def dedupe_key_getter(item: Dict[str, Any]) -> str:
            if not isinstance(item, dict):
                return str(item)
            name = item.get("name")
            tenant = item.get("tenant")
            normalized_name = name.strip() if isinstance(name, str) else str(name)
            normalized_tenant = tenant.strip() if isinstance(tenant, str) else str(tenant)
            return f"{normalized_name}|{normalized_tenant}"

        def worker(item: Dict[str, Any]) -> ReturnResponse:
            if not isinstance(item, dict):
                return self._fail(
                    msg="bulk_update_device_fields item must be dict",
                    data={"item": item},
                )
            allowed_keys = {"name", "tenant", "fields"}
            extra_keys = sorted(set(item.keys()) - allowed_keys)
            if extra_keys:
                return self._fail(
                    msg="bulk_update_device_fields item has unsupported keys",
                    data={"item": item, "unsupported_keys": extra_keys},
                )

            raw_name = item.get("name")
            if not isinstance(raw_name, str) or not raw_name.strip():
                return self._fail(
                    msg="bulk_update_device_fields item name is required",
                    data={"item": item},
                )
            name = raw_name.strip()

            fields = item.get("fields")
            if not isinstance(fields, dict) or not fields:
                return self._fail(
                    msg=f"device [{name}] fields are required",
                    data={"item": item},
                )

            tenant = item.get("tenant")
            if tenant is not None and not isinstance(tenant, str):
                return self._fail(
                    msg=f"device [{name}] tenant must be string or None",
                    data={"item": item},
                )
            if isinstance(tenant, str):
                tenant = tenant.strip() or None

            return self.update_device_fields(name=name, fields=fields, tenant=tenant)

        return self._run_parallel_batch(
            target="bulk_update_device_fields",
            items=updates,
            dedupe_key_getter=dedupe_key_getter,
            worker=worker,
            max_workers=max_workers,
        )

    def bulk_add_or_update_interfaces(
        self,
        interfaces: List[Dict[str, Any]],
        max_workers: int = 5,
    ) -> ReturnResponse:
        """Create or update interfaces in parallel.

        Args:
            interfaces: List of interface items compatible with
                ``add_or_update_interfaces`` arguments.
            max_workers: Maximum worker threads.

        Returns:
            ReturnResponse: Aggregated batch result.
        """

        def dedupe_key_getter(item: Dict[str, Any]) -> str:
            if not isinstance(item, dict):
                return str(item)
            device = item.get("device")
            name = item.get("name")
            tenant = item.get("tenant")
            normalized_device = device.strip() if isinstance(device, str) else str(device)
            normalized_name = name.strip() if isinstance(name, str) else str(name)
            normalized_tenant = tenant.strip() if isinstance(tenant, str) else str(tenant)
            return f"{normalized_device}|{normalized_name}|{normalized_tenant}"

        def worker(item: Dict[str, Any]) -> ReturnResponse:
            if not isinstance(item, dict):
                return self._fail(
                    msg="bulk_add_or_update_interfaces item must be dict",
                    data={"item": item},
                )
            allowed_keys = {
                "name",
                "device",
                "interface_type",
                "tenant",
                "label",
                "poe_mode",
                "poe_type",
                "description",
            }
            extra_keys = sorted(set(item.keys()) - allowed_keys)
            if extra_keys:
                return self._fail(
                    msg="bulk_add_or_update_interfaces item has unsupported keys",
                    data={"item": item, "unsupported_keys": extra_keys},
                )

            raw_device = item.get("device")
            if not isinstance(raw_device, str) or not raw_device.strip():
                return self._fail(
                    msg="bulk_add_or_update_interfaces item device is required",
                    data={"item": item},
                )

            raw_name = item.get("name")
            if not isinstance(raw_name, str) or not raw_name.strip():
                return self._fail(
                    msg="bulk_add_or_update_interfaces item name is required",
                    data={"item": item},
                )

            tenant = item.get("tenant")
            if tenant is not None and not isinstance(tenant, str):
                return self._fail(
                    msg="bulk_add_or_update_interfaces item tenant must be string or None",
                    data={"item": item},
                )
            if isinstance(tenant, str):
                tenant = tenant.strip() or None

            kwargs = Parse.remove_dict_none_value(
                {
                    "name": raw_name.strip(),
                    "device": raw_device.strip(),
                    "interface_type": item.get("interface_type"),
                    "tenant": tenant,
                    "label": item.get("label"),
                    "poe_mode": item.get("poe_mode"),
                    "poe_type": item.get("poe_type"),
                    "description": item.get("description"),
                }
            )
            return self.add_or_update_interfaces(**kwargs)

        return self._run_parallel_batch(
            target="bulk_add_or_update_interfaces",
            items=interfaces,
            dedupe_key_getter=dedupe_key_getter,
            worker=worker,
            max_workers=max_workers,
        )

    def get_device_role_id(self, name: Optional[str]) -> ReturnResponse:
        """Get device role ID by name.

        Args:
            name: Device role name.

        Returns:
            ReturnResponse: Device role ID in ``data``.
        """
        return self._query_single_id(
            "/api/dcim/device-roles/",
            {"name": name},
            "device-role",
        )

    def add_or_update_device_role(
        self,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        color: Literal["red", "orange", "yellow", "green", "blue", "purple", "gray", "black"] = "gray",
    ) -> ReturnResponse:
        """Create or update a device role.

        Args:
            name: Device role name.
            slug: Role slug.
            description: Description text.
            color: Color name.

        Returns:
            ReturnResponse: Upsert result.
        """
        color_map = {
            "red": "ff0000",
            "orange": "ffa500",
            "yellow": "ffff00",
            "green": "00ff00",
            "blue": "0000ff",
            "purple": "800080",
            "gray": "808080",
            "black": "000000",
        }

        role_id_response = self.get_device_role_id(name=name)
        if role_id_response.code != 0:
            return role_id_response

        payload = Parse.remove_dict_none_value(
            {
                "name": name,
                "slug": self._process_slug(name if slug is None else slug),
                "color": color_map[color],
                "description": description,
            }
        )

        return self._upsert_resource(
            "/api/dcim/device-roles/",
            role_id_response.data,
            payload,
            "device-role",
            str(name),
        )

    def get_contact_id(self, name: Optional[str]) -> ReturnResponse:
        """Get contact ID by name.

        Args:
            name: Contact name.

        Returns:
            ReturnResponse: Contact ID in ``data``.
        """
        return self._query_single_id(
            "/api/tenancy/contacts/",
            {"name": name},
            "contact",
        )

    def add_or_update_contacts(
        self,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        id_card: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ReturnResponse:
        """Create or update a contact.

        Args:
            name: Contact name.
            email: Contact email.
            phone: Contact phone.
            id_card: Custom ID card value.
            description: Description text.

        Returns:
            ReturnResponse: Upsert result.
        """
        contact_id_response = self.get_contact_id(name=name)
        if contact_id_response.code != 0:
            return contact_id_response

        payload = Parse.remove_dict_none_value(
            {
                "name": name,
                "email": email,
                "phone": phone,
                "description": description,
                "custom_fields": {"id_card": id_card},
            }
        )

        return self._upsert_resource(
            "/api/tenancy/contacts/",
            contact_id_response.data,
            payload,
            "contact",
            str(name),
        )

    def get_rack_id(self, name: Optional[str], tenant: Optional[str]) -> ReturnResponse:
        """Get rack ID by name and tenant.

        Args:
            name: Rack name.
            tenant: Tenant name.

        Returns:
            ReturnResponse: Rack ID in ``data``.
        """
        tenant_id_response = self.get_tenant_id(name=tenant)
        if tenant_id_response.code != 0:
            return tenant_id_response

        return self._query_single_id(
            "/api/dcim/racks/",
            {
                "name": name,
                "tenant_id": tenant_id_response.data,
            },
            "rack",
        )

    def add_or_update_rack(
        self,
        site: Optional[str] = None,
        name: Optional[str] = None,
        status: Literal["active", "reserved", "deprecated"] = "active",
        tenant: Optional[str] = None,
        u_height: Optional[int] = None,
        facility: Optional[str] = None,
    ) -> ReturnResponse:
        """Create or update a rack.

        Args:
            site: Site name.
            name: Rack name.
            status: Rack status.
            tenant: Tenant name.
            u_height: Rack height.
            facility: Facility value.

        Returns:
            ReturnResponse: Upsert result.
        """
        if status not in ["active", "reserved", "deprecated"]:
            return self._fail(msg=f"rack status [{status}] is invalid")

        site_id_response = self.get_site_id(name=site)
        if site_id_response.code != 0:
            return site_id_response

        tenant_id_response = self.get_tenant_id(name=tenant)
        if tenant_id_response.code != 0:
            return tenant_id_response

        rack_id_response = self.get_rack_id(name=name, tenant=tenant)
        if rack_id_response.code != 0:
            return rack_id_response

        payload = Parse.remove_dict_none_value(
            {
                "site": site_id_response.data,
                "name": name,
                "status": status,
                "tenant": tenant_id_response.data,
                "u_height": u_height,
                "facility": facility,
            }
        )

        return self._upsert_resource(
            "/api/dcim/racks/",
            rack_id_response.data,
            payload,
            "rack",
            str(name),
        )

    def get_tags_id(self, name: Optional[str]) -> ReturnResponse:
        """Get tag ID by name.

        Args:
            name: Tag name.

        Returns:
            ReturnResponse: Tag ID in ``data``.
        """
        return self._query_single_id(
            "/api/extras/tags/",
            {"name": name},
            "tag",
        )

    def add_or_update_tags(self, name: str, slug: str, color: str) -> ReturnResponse:
        """Create or update a tag.

        Args:
            name: Tag name.
            slug: Tag slug.
            color: Tag color.

        Returns:
            ReturnResponse: Upsert result.
        """
        tag_id_response = self.get_tags_id(name=name)
        if tag_id_response.code != 0:
            return tag_id_response

        payload = {"name": name, "slug": slug, "color": color}
        return self._upsert_resource(
            "/api/extras/tags/",
            tag_id_response.data,
            payload,
            "tag",
            name,
        )

    def get_interface_id(self, device: Optional[str], name: Optional[str]) -> ReturnResponse:
        """Get interface ID by device and name.

        Args:
            device: Device name.
            name: Interface name.

        Returns:
            ReturnResponse: Interface ID in ``data``.
        """
        return self._query_single_id(
            "/api/dcim/interfaces/",
            {"name": name, "device": device},
            "interface",
        )

    def add_or_update_interfaces(
        self,
        name: str,
        device: str,
        interface_type: Literal["1000base-t", "2.5gbase-t", "1gfc-sfp", "cisco-stackwise", "other"] = "other",
        tenant: Optional[str] = None,
        label: Optional[str] = None,
        poe_mode: Optional[Literal["pd", "pse"]] = None,
        poe_type: Optional[Literal["type2-ieee802.3at"]] = None,
        description: Optional[str] = None,
    ) -> ReturnResponse:
        """Create or update an interface.

        Args:
            name: Interface name.
            device: Device name.
            interface_type: Interface type.
            tenant: Tenant name.
            label: Interface label.
            poe_mode: PoE mode.
            poe_type: PoE type.
            description: Description text.

        Returns:
            ReturnResponse: Upsert result.
        """
        tenant_id_response = self.get_tenant_id(name=tenant)
        if tenant_id_response.code != 0:
            return tenant_id_response

        device_id_response = self.get_device_id(
            name=device,
            tenant_id=tenant_id_response.data,
        )
        if device_id_response.code != 0:
            return device_id_response

        interface_id_response = self.get_interface_id(name=name, device=device)
        if interface_id_response.code != 0:
            return interface_id_response

        payload = Parse.remove_dict_none_value(
            {
                "name": name,
                "device": device_id_response.data,
                "type": interface_type,
                "label": label,
                "poe_mode": poe_mode,
                "poe_type": poe_type,
                "description": description,
            }
        )

        return self._upsert_resource(
            "/api/dcim/interfaces/",
            interface_id_response.data,
            payload,
            "interface",
            name,
        )

    def get_contact_role_id(self, name: Optional[str]) -> ReturnResponse:
        """Get contact role ID by name.

        Args:
            name: Contact role name.

        Returns:
            ReturnResponse: Contact role ID in ``data``.
        """
        return self._query_single_id(
            "/api/tenancy/contact-roles/",
            {"name": name},
            "contact-role",
        )

    def add_or_update_contact_role(self, name: str) -> ReturnResponse:
        """Create or update a contact role.

        Args:
            name: Contact role name.

        Returns:
            ReturnResponse: Upsert result.
        """
        contact_role_id_response = self.get_contact_role_id(name=name)
        if contact_role_id_response.code != 0:
            return contact_role_id_response

        payload = {"name": name, "slug": self._process_slug(name)}
        return self._upsert_resource(
            "/api/tenancy/contact-roles/",
            contact_role_id_response.data,
            payload,
            "contact-role",
            name,
        )

    def is_contact_assignmentd(
        self,
        contact_id: int,
        object_type: Literal["dcim.site", "dcim.location", "dcim.rack", "dcim.device", "dcim.interface"],
        role: str,
    ) -> ReturnResponse:
        """Check whether a contact assignment exists.

        Args:
            contact_id: Contact ID.
            object_type: Object type.
            role: Contact role ID.

        Returns:
            ReturnResponse: ``data`` is a bool value.
        """
        response = self._request_with_retry(
            "GET",
            "/api/tenancy/contact-assignments/",
            params={
                "contact_id": contact_id,
                "object_type": object_type,
                "role_id": role,
            },
        )
        if response.code != 0:
            return response

        results = self._extract_results(response.data)
        exists = len(results) > 0
        return self._ok(
            msg="contact-assignment exists" if exists else "contact-assignment not found",
            data=exists,
        )

    def get_contact_assignment_id(
        self,
        contact_id: int,
        object_type: Literal["dcim.site", "dcim.location", "dcim.rack", "dcim.device", "dcim.interface"],
        role: str,
    ) -> ReturnResponse:
        """Get contact assignment ID.

        Args:
            contact_id: Contact ID.
            object_type: Object type.
            role: Contact role ID.

        Returns:
            ReturnResponse: Assignment ID in ``data``.
        """
        response = self._request_with_retry(
            "GET",
            "/api/tenancy/contact-assignments/",
            params={
                "contact_id": contact_id,
                "object_type": object_type,
                "role_id": role,
            },
        )
        if response.code != 0:
            return response

        results = self._extract_results(response.data)
        if not results:
            return self._ok(msg="contact-assignment not found", data=None)
        return self._ok(msg="contact-assignment found", data=results[0].get("id"))

    def assign_contact_to_object(
        self,
        contact: str,
        object_type: Literal["dcim.site", "dcim.location", "dcim.rack", "dcim.device", "dcim.interface"],
        object_name: str,
        role: str,
        priority: Literal["primary", "secondary", "tertiary", "inactive"] = "primary",
        tenant: Optional[str] = None,
    ) -> ReturnResponse:
        """Assign a contact to a NetBox object.

        Args:
            contact: Contact name.
            object_type: Object type.
            object_name: Object name.
            role: Contact role name.
            priority: Assignment priority.
            tenant: Optional tenant for rack/device lookup.

        Returns:
            ReturnResponse: Assignment upsert result.
        """
        object_id_response: ReturnResponse
        if object_type == "dcim.site":
            object_id_response = self.get_site_id(name=object_name)
        elif object_type == "dcim.location":
            object_id_response = self.get_dcim_location_id(name=object_name)
        elif object_type == "dcim.rack":
            object_id_response = self.get_rack_id(name=object_name, tenant=tenant)
        elif object_type == "dcim.device":
            tenant_id_response = self.get_tenant_id(name=tenant)
            if tenant_id_response.code != 0:
                return tenant_id_response
            object_id_response = self.get_device_id(
                name=object_name,
                tenant_id=tenant_id_response.data,
            )
        elif object_type == "dcim.interface":
            if "/" in object_name:
                device_name, interface_name = object_name.split("/", 1)
            else:
                device_name, interface_name = object_name, object_name
            object_id_response = self.get_interface_id(device=device_name, name=interface_name)
        else:
            return self._fail(msg=f"object_type [{object_type}] is invalid")

        if object_id_response.code != 0:
            return object_id_response

        contact_id_response = self.get_contact_id(name=contact)
        if contact_id_response.code != 0:
            return contact_id_response

        role_id_response = self.get_contact_role_id(name=role)
        if role_id_response.code != 0:
            return role_id_response

        payload = {
            "contact": contact_id_response.data,
            "object_type": object_type,
            "object_id": object_id_response.data,
            "role": role_id_response.data,
            "priority": priority,
        }

        exists_response = self.is_contact_assignmentd(
            contact_id=contact_id_response.data,
            object_type=object_type,
            role=str(role_id_response.data),
        )
        if exists_response.code != 0:
            return exists_response

        if bool(exists_response.data):
            assignment_id_response = self.get_contact_assignment_id(
                contact_id=contact_id_response.data,
                object_type=object_type,
                role=str(role_id_response.data),
            )
            if assignment_id_response.code != 0:
                return assignment_id_response
            payload["id"] = assignment_id_response.data
            response = self._request_with_retry(
                "PATCH",
                "/api/tenancy/contact-assignments/",
                json_data=[payload],
            )
            if response.code != 0:
                return self._fail(msg="contact-assignment update failed", data=response.data)
            return self._ok(msg="contact-assignment updated", data=response.data)

        response = self._request_with_retry(
            "POST",
            "/api/tenancy/contact-assignments/",
            json_data=payload,
        )
        if response.code != 0:
            return self._fail(msg="contact-assignment create failed", data=response.data)
        return self._ok(msg="contact-assignment created", data=response.data)

    def get_object_type(self) -> ReturnResponse:
        """Get all object types.

        Returns:
            ReturnResponse: Object type list in ``data``.
        """
        response = self._request_with_retry("GET", "/api/extras/object-types/")
        if response.code != 0:
            return response

        if isinstance(response.data, dict):
            results = response.data.get("results")
            if isinstance(results, list):
                return self._ok(msg="object-types fetched", data=results)
        return self._ok(msg="object-types fetched", data=response.data)

    def get_object_type_id(
        self,
        name: Literal[
            "dcim.site",
            "dcim.location",
            "dcim.rack",
            "dcim.device",
            "dcim.interface",
            "dcim.device-type",
            "dcim.manufacturer",
            "dcim.virtual-chassis",
            "dcim.cable",
            "dcim.power-outlet",
            "dcim.power-port",
            "dcim.power-feed",
            "dcim.power-panel",
            "dcim.power-outlet-template",
            "dcim.power-port-template",
            "dcim.power-feed-template",
            "dcim.power-panel-template",
        ],
    ) -> ReturnResponse:
        """Get object type ID by app label and model.

        Args:
            name: Object type full name.

        Returns:
            ReturnResponse: Object type ID in ``data``.
        """
        if "." not in name:
            return self._fail(msg=f"object type [{name}] is invalid")
        app_label, model = name.split(".", 1)
        return self._query_single_id(
            "/api/extras/object-types/",
            {"app_label": app_label, "model": model},
            "object-type",
        )

    def add_or_update_sites(self, name: str, slug: str, tenant: Optional[str]) -> ReturnResponse:
        """Create or update a site.

        Args:
            name: Site name.
            slug: Site slug.
            tenant: Tenant name.

        Returns:
            ReturnResponse: Upsert result.
        """
        tenant_id_response = self.get_tenant_id(name=tenant)
        if tenant_id_response.code != 0:
            return tenant_id_response

        site_id_response = self.get_site_id(name=name)
        if site_id_response.code != 0:
            return site_id_response

        payload = Parse.remove_dict_none_value(
            {
                "name": name,
                "slug": slug,
                "tenant": tenant_id_response.data,
            }
        )
        return self._upsert_resource(
            "/api/dcim/sites/",
            site_id_response.data,
            payload,
            "site",
            name,
        )

    def get_devices(
        self,
        tenant: Optional[str] = None,
        device_type: Optional[str] = None,
        manufacturer: Optional[str] = None,
    ) -> ReturnResponse:
        """Get device list with pagination.

        Args:
            tenant: Tenant filter.
            device_type: Device type filter.
            manufacturer: Manufacturer filter.

        Returns:
            ReturnResponse: Device list in ``data``.
        """
        manufacturer_id_response = self.get_manufacturer_id(name=manufacturer)
        if manufacturer_id_response.code != 0:
            return manufacturer_id_response

        params = Parse.remove_dict_none_value(
            {
                "tenant": tenant,
                "device_type": device_type,
                "manufacturer_id": manufacturer_id_response.data,
                "limit": 0,
            }
        )

        results: List[Dict[str, Any]] = []
        next_url: Optional[str] = "/api/dcim/devices/"
        next_params: Optional[Dict[str, Any]] = params

        while next_url:
            response = self._request_with_retry("GET", next_url, params=next_params)
            if response.code != 0:
                return response

            if not isinstance(response.data, dict):
                return self._fail(msg="device list payload is invalid", data=response.data)

            page_results = response.data.get("results")
            if isinstance(page_results, list):
                results.extend([item for item in page_results if isinstance(item, dict)])

            raw_next = response.data.get("next")
            next_url = raw_next if isinstance(raw_next, str) and raw_next else None
            next_params = None

        return self._ok(msg="devices fetched", data=results)

    def get_power_port_id(self, device: Optional[str], name: Optional[str]) -> ReturnResponse:
        """Get power port ID by device and name.

        Args:
            device: Device name.
            name: Power port name.

        Returns:
            ReturnResponse: Power port ID in ``data``.
        """
        return self._query_single_id(
            "/api/dcim/power-ports/",
            {"name": name, "device": device},
            "power-port",
        )

    def add_or_update_power_ports(
        self,
        device: str,
        name: str,
        power_type: Literal["iec-60320-c14", "other"],
        label: Optional[str] = None,
        maximum_draw: Optional[int] = None,
        allocated_draw: Optional[int] = None,
        mark_connected: bool = True,
        description: Optional[str] = None,
    ) -> ReturnResponse:
        """Create or update a power port.

        Args:
            device: Device name.
            name: Power port name.
            power_type: Power type.
            label: Label value.
            maximum_draw: Maximum power draw.
            allocated_draw: Allocated power draw.
            mark_connected: Connected flag.
            description: Description text.

        Returns:
            ReturnResponse: Upsert result.
        """
        device_id_response = self.get_device_id(name=device)
        if device_id_response.code != 0:
            return device_id_response

        power_port_id_response = self.get_power_port_id(name=name, device=device)
        if power_port_id_response.code != 0:
            return power_port_id_response

        payload = Parse.remove_dict_none_value(
            {
                "device": device_id_response.data,
                "name": name,
                "type": power_type,
                "label": label,
                "maximum_draw": maximum_draw,
                "allocated_draw": allocated_draw,
                "mark_connected": mark_connected,
                "description": description,
            }
        )

        return self._upsert_resource(
            "/api/dcim/power-ports/",
            power_port_id_response.data,
            payload,
            "power-port",
            f"{device}:{name}",
        )

    def get_console_port_id(self, device: Optional[str], name: Optional[str]) -> ReturnResponse:
        """Get console port ID by device and name.

        Args:
            device: Device name.
            name: Console port name.

        Returns:
            ReturnResponse: Console port ID in ``data``.
        """
        return self._query_single_id(
            "/api/dcim/console-ports/",
            {"name": name, "device": device},
            "console-port",
        )

    def add_or_update_console_port(
        self,
        device: str,
        name: str,
        port_type: Literal["rj-45"] = "rj-45",
        description: Optional[str] = None,
    ) -> ReturnResponse:
        """Create or update a console port.

        Args:
            device: Device name.
            name: Console port name.
            port_type: Console port type.
            description: Description text.

        Returns:
            ReturnResponse: Upsert result.
        """
        device_id_response = self.get_device_id(name=device)
        if device_id_response.code != 0:
            return device_id_response

        console_port_id_response = self.get_console_port_id(name=name, device=device)
        if console_port_id_response.code != 0:
            return console_port_id_response

        payload = Parse.remove_dict_none_value(
            {
                "device": device_id_response.data,
                "name": name,
                "type": port_type,
                "description": description,
            }
        )

        return self._upsert_resource(
            "/api/dcim/console-ports/",
            console_port_id_response.data,
            payload,
            "console-port",
            f"{device}:{name}",
        )
