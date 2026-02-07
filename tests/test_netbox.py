#!/usr/bin/env python3

"""Basic Netbox client smoke tests."""

from pytbox.netbox.client import NetboxClient


def test_get_update_comments_returns_text() -> None:
    """Ensure pure helper returns plain text."""
    client = NetboxClient(url="https://netbox.example.com", token="token")
    result = client.get_update_comments(source="unit-test")
    assert isinstance(result, str)
    assert "Source: unit-test" in result
