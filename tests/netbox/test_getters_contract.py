#!/usr/bin/env python3

"""Getter contract tests for NetBox client."""

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


@pytest.mark.parametrize(
    ("method_name", "kwargs"),
    [
        ("get_org_sites_regions", {}),
        ("get_region_id", {"name": "R1"}),
        ("get_dcim_site_id", {"name": "S1"}),
        ("get_dcim_location_id", {"name": "L1"}),
        ("get_ipam_ipaddress_id", {"address": "10.0.0.1/24"}),
        ("get_tenants_id", {"name": "T1"}),
        ("get_ipam_prefix_id", {"prefix": "10.0.0.0/24"}),
        ("get_prefix_id_by_prefix", {"prefix": "10.0.0.0/24"}),
        ("get_ipam_ip_range_id", {"start_address": "10.0.0.1", "end_address": "10.0.0.9"}),
        ("get_manufacturer_id_by_name", {"name": "Cisco"}),
        ("get_device_type_id", {"model": "MR44"}),
        ("get_manufacturer_id", {"name": "Cisco"}),
        ("get_device_id_by_name", {"name": "device-1"}),
        ("get_tenant_id", {"name": "tenant-1"}),
        ("get_site_id", {"name": "site-1"}),
        ("get_device_id", {"name": "device-1", "tenant_id": "1"}),
        ("get_device_type_id_by_name", {"name": "MR44"}),
        ("get_device_role_id", {"name": "router"}),
        ("get_contact_id", {"name": "contact-1"}),
        ("get_rack_id", {"name": "rack-1", "tenant": "tenant-1"}),
        ("get_tags_id", {"name": "tag-1"}),
        ("get_interface_id", {"device": "device-1", "name": "Gi0/1"}),
        ("get_contact_role_id", {"name": "owner"}),
        ("is_contact_assignmentd", {"contact_id": 1, "object_type": "dcim.site", "role": "1"}),
        ("get_contact_assignment_id", {"contact_id": 1, "object_type": "dcim.site", "role": "1"}),
        ("get_object_type", {}),
        ("get_object_type_id", {"name": "dcim.site"}),
        ("get_devices", {"tenant": "tenant-1", "device_type": "MR44", "manufacturer": "Cisco"}),
        ("get_power_port_id", {"device": "device-1", "name": "PWR1"}),
        ("get_console_port_id", {"device": "device-1", "name": "CON1"}),
    ],
)
def test_getter_methods_return_returnresponse(
    client: NetboxClient,
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    kwargs: dict[str, Any],
) -> None:
    """Every getter should return ReturnResponse.

    Args:
        client: NetBox client fixture.
        monkeypatch: Pytest monkeypatch fixture.
        method_name: Target method name.
        kwargs: Method kwargs.
    """

    def fake_request(
        method: str,
        api_url: str,
        params: dict[str, Any] | None = None,
        json_data: Any = None,
        data: Any = None,
    ) -> ReturnResponse:
        _ = method, params, json_data, data
        if api_url == "/api/extras/object-types/":
            return ReturnResponse(
                code=0,
                msg="ok",
                data={"count": 1, "results": [{"id": 10, "app_label": "dcim", "model": "site"}]},
            )
        return ReturnResponse(code=0, msg="ok", data={"count": 1, "results": [{"id": 1}], "next": None})

    monkeypatch.setattr(client, "_request_with_retry", fake_request)

    result = getattr(client, method_name)(**kwargs)

    assert isinstance(result, ReturnResponse)


def test_get_ipam_prefix_id_uses_prefix_filter(
    client: NetboxClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prefix lookup should use prefix parameter instead of shadowed variable."""
    captured_params: dict[str, Any] = {}

    def fake_request(
        method: str,
        api_url: str,
        params: dict[str, Any] | None = None,
        json_data: Any = None,
        data: Any = None,
    ) -> ReturnResponse:
        _ = method, api_url, json_data, data
        if params is not None:
            captured_params.update(params)
        return ReturnResponse(code=0, msg="ok", data={"count": 1, "results": [{"id": 9}]})

    monkeypatch.setattr(client, "_request_with_retry", fake_request)

    result = client.get_ipam_prefix_id(prefix="10.0.0.0/24")

    assert result.code == 0
    assert result.data == 9
    assert captured_params["prefix"] == "10.0.0.0/24"


def test_get_device_type_id_by_name_fallback_stops(
    client: NetboxClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fallback from custom type to other should terminate safely."""
    calls: list[str | None] = []

    def fake_get_device_type_id(model: str | None) -> ReturnResponse:
        calls.append(model)
        return ReturnResponse(code=0, msg="not found", data=None)

    monkeypatch.setattr(client, "get_device_type_id", fake_get_device_type_id)

    result = client.get_device_type_id_by_name(name="custom-type")

    assert result.code == 0
    assert result.data is None
    assert calls == ["custom-type", "other"]


def test_get_devices_paginates(
    client: NetboxClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Device listing should iterate pagination via next URLs."""
    calls: list[str] = []

    def fake_request(
        method: str,
        api_url: str,
        params: dict[str, Any] | None = None,
        json_data: Any = None,
        data: Any = None,
    ) -> ReturnResponse:
        _ = method, params, json_data, data
        calls.append(api_url)
        if len(calls) == 1:
            return ReturnResponse(
                code=0,
                msg="ok",
                data={"results": [{"id": 1}], "next": "https://netbox.example.com/api/dcim/devices/?offset=1"},
            )
        return ReturnResponse(code=0, msg="ok", data={"results": [{"id": 2}], "next": None})

    monkeypatch.setattr(client, "_request_with_retry", fake_request)
    monkeypatch.setattr(client, "get_manufacturer_id", lambda name: ReturnResponse(code=0, msg="ok", data=1))

    result = client.get_devices(tenant="tenant-1", device_type="MR44", manufacturer="Cisco")

    assert result.code == 0
    assert result.data == [{"id": 1}, {"id": 2}]
    assert len(calls) == 2
