#!/usr/bin/env python3

"""Mutation contract tests for NetBox client."""

from __future__ import annotations

from typing import Any

import pytest

from pytbox.netbox.client import NetboxClient
from pytbox.schemas.response import ReturnResponse


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> NetboxClient:
    """Create test client.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        NetboxClient: Initialized client.
    """
    monkeypatch.setattr("pytbox.netbox.client.pynetbox.api", lambda *_args, **_kwargs: object())
    return NetboxClient(url="https://netbox.example.com", token="token")


def _ok_response(data: Any = 1) -> ReturnResponse:
    """Build a shared success response.

    Args:
        data: Optional payload.

    Returns:
        ReturnResponse: Success response.
    """
    return ReturnResponse(code=0, msg="ok", data=data)


def _patch_common_dependencies(client: NetboxClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch common dependencies for mutation contract tests.

    Args:
        client: NetBox client instance.
        monkeypatch: Pytest monkeypatch fixture.
    """

    def ok_id(*_args: Any, **_kwargs: Any) -> ReturnResponse:
        return _ok_response(1)

    for method_name in [
        "get_region_id",
        "get_site_id",
        "get_dcim_site_id",
        "get_dcim_location_id",
        "get_ipam_ipaddress_id",
        "get_tenants_id",
        "get_prefix_id_by_prefix",
        "get_ipam_ip_range_id",
        "get_manufacturer_id_by_name",
        "get_device_type_id",
        "get_manufacturer_id",
        "get_device_id_by_name",
        "get_tenant_id",
        "get_device_id",
        "get_device_type_id_by_name",
        "get_device_role_id",
        "get_contact_id",
        "get_rack_id",
        "get_tags_id",
        "get_interface_id",
        "get_contact_role_id",
        "get_contact_assignment_id",
        "get_power_port_id",
        "get_console_port_id",
    ]:
        monkeypatch.setattr(client, method_name, ok_id)

    monkeypatch.setattr(
        client,
        "is_contact_assignmentd",
        lambda *_args, **_kwargs: _ok_response(False),
    )
    monkeypatch.setattr(
        client,
        "_request_with_retry",
        lambda *_args, **_kwargs: _ok_response({"count": 1, "results": [{"id": 1}], "next": None}),
    )
    monkeypatch.setattr(
        client,
        "_upsert_resource",
        lambda *_args, **_kwargs: _ok_response({"id": 1}),
    )


@pytest.mark.parametrize(
    ("method_name", "kwargs"),
    [
        ("add_or_update_region", {"name": "region-1"}),
        ("add_or_update_org_sites_sites", {"name": "site-1"}),
        ("add_or_update_dcim_location", {"name": "loc-1"}),
        ("assign_ipaddress_to_interface", {"address": "10.0.0.1/24", "device": "device-1", "interface_name": "Gi0/1"}),
        ("add_or_update_ipam_ipaddress", {"address": "10.0.0.1/24"}),
        ("add_or_update_ipam_prefix", {"prefix": "10.0.0.0/24"}),
        ("add_or_update_ip_ranges", {"start_address": "10.0.0.1", "end_address": "10.0.0.9"}),
        ("add_or_update_tenants", {"name": "tenant-1"}),
        ("add_or_update_device_type", {"model": "MR44"}),
        ("add_or_update_manufacturer", {"name": "Cisco"}),
        ("add_or_update_device", {"name": "device-1"}),
        ("set_primary_ip4_to_device", {"device_name": "device-1", "tenant": "tenant-1", "primary_ip4": "10.0.0.1/24"}),
        ("add_or_update_device_role", {"name": "router"}),
        ("add_or_update_contacts", {"name": "contact-1"}),
        ("add_or_update_rack", {"site": "site-1", "name": "rack-1"}),
        ("add_or_update_tags", {"name": "tag-1", "slug": "tag-1", "color": "ff0000"}),
        ("add_or_update_interfaces", {"name": "Gi0/1", "device": "device-1"}),
        ("add_or_update_contact_role", {"name": "owner"}),
        ("assign_contact_to_object", {"contact": "contact-1", "object_type": "dcim.site", "object_name": "site-1", "role": "owner"}),
        ("add_or_update_sites", {"name": "site-1", "slug": "site-1", "tenant": "tenant-1"}),
        ("add_or_update_power_ports", {"device": "device-1", "name": "PWR1", "power_type": "other"}),
        ("add_or_update_console_port", {"device": "device-1", "name": "CON1"}),
    ],
)
def test_mutation_methods_return_returnresponse(
    client: NetboxClient,
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    kwargs: dict[str, Any],
) -> None:
    """Every mutation should return ReturnResponse.

    Args:
        client: NetBox client fixture.
        monkeypatch: Pytest monkeypatch fixture.
        method_name: Target method name.
        kwargs: Method kwargs.
    """
    _patch_common_dependencies(client, monkeypatch)

    result = getattr(client, method_name)(**kwargs)

    assert isinstance(result, ReturnResponse)


def test_assign_contact_to_object_uses_location_getter(
    client: NetboxClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Location assignment path should call get_dcim_location_id."""
    called = {"location": 0}

    def fake_get_dcim_location_id(name: str | None) -> ReturnResponse:
        _ = name
        called["location"] += 1
        return _ok_response(9)

    _patch_common_dependencies(client, monkeypatch)
    monkeypatch.setattr(client, "get_dcim_location_id", fake_get_dcim_location_id)

    result = client.assign_contact_to_object(
        contact="contact-1",
        object_type="dcim.location",
        object_name="loc-1",
        role="owner",
    )

    assert result.code == 0
    assert called["location"] == 1


def test_add_or_update_org_sites_sites_generates_slug_when_missing(
    client: NetboxClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Site upsert should auto-generate slug when slug is missing."""
    captured_payload: dict[str, Any] = {}

    _patch_common_dependencies(client, monkeypatch)
    monkeypatch.setattr(client, "get_site_id", lambda name: _ok_response(None))

    def fake_upsert(
        api_url: str,
        resource_id: Any,
        payload: dict[str, Any],
        resource_name: str,
        resource_key: str,
    ) -> ReturnResponse:
        _ = api_url, resource_id, resource_name, resource_key
        captured_payload.update(payload)
        return _ok_response(payload)

    monkeypatch.setattr(client, "_upsert_resource", fake_upsert)

    result = client.add_or_update_org_sites_sites(name="测试站点", slug=None)

    assert result.code == 0
    assert captured_payload["slug"]


def test_process_gps_accepts_multiple_types(client: NetboxClient) -> None:
    """GPS parser should support str/float/int/None safely."""
    assert client._process_gps("120.126") == 120.13
    assert client._process_gps(121.234) == 121.23
    assert client._process_gps(122) == 122.0
    assert client._process_gps(None) is None
    assert client._process_gps("invalid") is None


def test_all_public_methods_covered(client: NetboxClient) -> None:
    """Guardrail to ensure public method count stays stable with coverage."""
    public_methods = [
        name
        for name in dir(client)
        if not name.startswith("_") and callable(getattr(client, name))
    ]

    expected_methods = {
        "get_update_comments",
        "get_org_sites_regions",
        "get_region_id",
        "add_or_update_region",
        "get_dcim_site_id",
        "add_or_update_org_sites_sites",
        "get_dcim_location_id",
        "add_or_update_dcim_location",
        "get_ipam_ipaddress_id",
        "get_tenants_id",
        "assign_ipaddress_to_interface",
        "add_or_update_ipam_ipaddress",
        "get_ipam_prefix_id",
        "get_prefix_id_by_prefix",
        "add_or_update_ipam_prefix",
        "get_ipam_ip_range_id",
        "add_or_update_ip_ranges",
        "add_or_update_tenants",
        "get_manufacturer_id_by_name",
        "add_or_update_device_type",
        "get_device_type_id",
        "get_manufacturer_id",
        "add_or_update_manufacturer",
        "get_device_id_by_name",
        "get_tenant_id",
        "get_site_id",
        "get_device_id",
        "get_device_type_id_by_name",
        "add_or_update_device",
        "set_primary_ip4_to_device",
        "get_device_role_id",
        "add_or_update_device_role",
        "get_contact_id",
        "add_or_update_contacts",
        "get_rack_id",
        "add_or_update_rack",
        "get_tags_id",
        "add_or_update_tags",
        "get_interface_id",
        "add_or_update_interfaces",
        "get_contact_role_id",
        "add_or_update_contact_role",
        "is_contact_assignmentd",
        "get_contact_assignment_id",
        "assign_contact_to_object",
        "get_object_type",
        "get_object_type_id",
        "add_or_update_sites",
        "get_devices",
        "get_power_port_id",
        "add_or_update_power_ports",
        "get_console_port_id",
        "add_or_update_console_port",
    }

    assert expected_methods.issubset(set(public_methods))
