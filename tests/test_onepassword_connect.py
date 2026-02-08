#!/usr/bin/env python3
"""Unit tests for OnePasswordConnect."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

from pytbox.onepassword_connect import OnePasswordConnect


class DummyField:
    """Simple field object used by tests.

    Args:
        purpose: 1Password field purpose.
        label: 1Password field label.
        value: Stored field value.
        totp: Optional totp value.
    """

    def __init__(
        self,
        purpose: str,
        label: str,
        value: Any,
        totp: str | None = None,
    ) -> None:
        self.purpose = purpose
        self.label = label
        self.value = value
        self.totp = totp


@pytest.fixture
def fake_client() -> SimpleNamespace:
    """Build a fake SDK client.

    Returns:
        SimpleNamespace: Fake client with mocked methods.
    """
    return SimpleNamespace(
        session=SimpleNamespace(timeout=None),
        create_item=Mock(return_value=SimpleNamespace(id="created")),
        delete_item=Mock(return_value=None),
        get_item=Mock(),
        get_item_by_title=Mock(),
        update_item=Mock(),
        get_items=Mock(return_value=[]),
    )


@pytest.fixture
def oc(
    monkeypatch: pytest.MonkeyPatch, fake_client: SimpleNamespace
) -> OnePasswordConnect:
    """Create OnePasswordConnect instance with mocked SDK client.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        fake_client: Mocked SDK client.

    Returns:
        OnePasswordConnect: Client wrapper instance for tests.
    """
    monkeypatch.setattr(
        "pytbox.onepassword_connect.new_client_from_environment",
        lambda: fake_client,
    )
    monkeypatch.setattr("pytbox.onepassword_connect.time.sleep", lambda _seconds: None)
    return OnePasswordConnect(
        vault_id="vault-1",
        request_timeout=2.5,
        max_retries=3,
        retry_backoff_base=0.0,
        idempotency_ttl_seconds=300,
    )


def test_init_configures_timeout(fake_client: SimpleNamespace, oc: OnePasswordConnect) -> None:
    """Ensure session timeout is configured during initialization.

    Args:
        fake_client: Mocked SDK client.
        oc: Initialized wrapper instance.
    """
    del oc
    assert fake_client.session.timeout == 2.5


def test_delete_item_uses_sdk_argument_order(
    fake_client: SimpleNamespace, oc: OnePasswordConnect
) -> None:
    """Verify delete_item calls SDK with item_id before vault_id.

    Args:
        fake_client: Mocked SDK client.
        oc: Initialized wrapper instance.
    """
    oc.delete_item(item_id="item-1")
    fake_client.delete_item.assert_called_once_with("item-1", "vault-1")


def test_update_item_only_updates_explicit_fields(
    fake_client: SimpleNamespace, oc: OnePasswordConnect
) -> None:
    """Verify update_item does not overwrite omitted fields with None.

    Args:
        fake_client: Mocked SDK client.
        oc: Initialized wrapper instance.
    """
    existing_item = SimpleNamespace(
        title="old-title",
        tags=["old"],
        fields=[
            DummyField(purpose="USERNAME", label="username", value="old-user"),
            DummyField(purpose="PASSWORD", label="password", value="old-pass"),
            DummyField(purpose="NOTES", label="notes", value="old-notes"),
        ],
    )
    fake_client.get_item.return_value = existing_item
    fake_client.update_item.return_value = existing_item

    updated = oc.update_item(item_id="item-1", username="new-user", tags=[])

    assert updated is existing_item
    assert existing_item.title == "old-title"
    assert existing_item.tags == []
    assert existing_item.fields[0].value == "new-user"
    assert existing_item.fields[1].value == "old-pass"
    assert existing_item.fields[2].value == "old-notes"
    fake_client.update_item.assert_called_once_with("item-1", "vault-1", existing_item)


def test_search_item_with_title_only(
    fake_client: SimpleNamespace, oc: OnePasswordConnect
) -> None:
    """Verify search_item builds title filter correctly.

    Args:
        fake_client: Mocked SDK client.
        oc: Initialized wrapper instance.
    """
    oc.search_item(title="demo")
    fake_client.get_items.assert_called_once_with(
        "vault-1",
        filter_query='title eq "demo"',
    )


def test_search_item_with_tag_only(
    fake_client: SimpleNamespace, oc: OnePasswordConnect
) -> None:
    """Verify search_item builds tag filter correctly.

    Args:
        fake_client: Mocked SDK client.
        oc: Initialized wrapper instance.
    """
    oc.search_item(tag="prod")
    fake_client.get_items.assert_called_once_with(
        "vault-1",
        filter_query='tag eq "prod"',
    )


def test_search_item_with_title_and_tag(
    fake_client: SimpleNamespace, oc: OnePasswordConnect
) -> None:
    """Verify search_item combines title and tag with AND.

    Args:
        fake_client: Mocked SDK client.
        oc: Initialized wrapper instance.
    """
    oc.search_item(title="demo", tag="prod")
    fake_client.get_items.assert_called_once_with(
        "vault-1",
        filter_query='title eq "demo" and tag eq "prod"',
    )


def test_get_item_by_title_returns_dict(
    fake_client: SimpleNamespace, oc: OnePasswordConnect
) -> None:
    """Verify get_item_by_title returns field dictionary by default.

    Args:
        fake_client: Mocked SDK client.
        oc: Initialized wrapper instance.
    """
    fake_client.get_item_by_title.return_value = SimpleNamespace(
        fields=[
            DummyField(purpose="USERNAME", label="username", value="alice"),
            DummyField(purpose="PASSWORD", label="password", value="secret"),
        ]
    )

    result = oc.get_item_by_title(title="demo")

    assert result == {"username": "alice", "password": "secret"}


def test_get_item_by_title_returns_totp(
    fake_client: SimpleNamespace, oc: OnePasswordConnect
) -> None:
    """Verify get_item_by_title returns totp when requested.

    Args:
        fake_client: Mocked SDK client.
        oc: Initialized wrapper instance.
    """
    fake_client.get_item_by_title.return_value = SimpleNamespace(
        fields=[
            DummyField(purpose="USERNAME", label="username", value="alice", totp=None),
            DummyField(
                purpose="TOTP",
                label="otp",
                value=None,
                totp="123456",
            ),
        ]
    )

    result = oc.get_item_by_title(title="demo", totp=True)

    assert result == "123456"


def test_retry_success_after_transient_failures(
    monkeypatch: pytest.MonkeyPatch, fake_client: SimpleNamespace
) -> None:
    """Verify external call retries and succeeds on the third attempt.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        fake_client: Mocked SDK client.
    """
    state = {"calls": 0}

    def _flaky_get_item(item_id: str, vault_id: str) -> Any:
        state["calls"] += 1
        if state["calls"] < 3:
            raise RuntimeError("temporary failure")
        return {"item_id": item_id, "vault_id": vault_id}

    fake_client.get_item.side_effect = _flaky_get_item
    monkeypatch.setattr(
        "pytbox.onepassword_connect.new_client_from_environment",
        lambda: fake_client,
    )
    monkeypatch.setattr("pytbox.onepassword_connect.time.sleep", lambda _seconds: None)
    client = OnePasswordConnect(
        vault_id="vault-1",
        max_retries=3,
        retry_backoff_base=0.0,
    )

    result = client.get_item(item_id="item-1")

    assert state["calls"] == 3
    assert result == {"item_id": "item-1", "vault_id": "vault-1"}


def test_retry_is_capped_to_three_attempts(
    monkeypatch: pytest.MonkeyPatch, fake_client: SimpleNamespace
) -> None:
    """Verify retries are capped to 3 even when larger max_retries is passed.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        fake_client: Mocked SDK client.
    """
    fake_client.get_items.side_effect = RuntimeError("always fails")
    monkeypatch.setattr(
        "pytbox.onepassword_connect.new_client_from_environment",
        lambda: fake_client,
    )
    monkeypatch.setattr("pytbox.onepassword_connect.time.sleep", lambda _seconds: None)
    client = OnePasswordConnect(
        vault_id="vault-1",
        max_retries=10,
        retry_backoff_base=0.0,
    )

    with pytest.raises(RuntimeError):
        client.search_item(title="demo")
    assert fake_client.get_items.call_count == 3


def test_create_item_is_idempotent_within_ttl(
    fake_client: SimpleNamespace, oc: OnePasswordConnect
) -> None:
    """Verify duplicate create requests are served from idempotency cache.

    Args:
        fake_client: Mocked SDK client.
        oc: Initialized wrapper instance.
    """
    first = oc.create_item(
        name="demo",
        username="alice",
        password="secret",
        notes="memo",
        tags=["prod"],
    )
    second = oc.create_item(
        name="demo",
        username="alice",
        password="secret",
        notes="memo",
        tags=["prod"],
    )

    assert first is second
    assert fake_client.create_item.call_count == 1


def test_update_item_is_idempotent_within_ttl(
    fake_client: SimpleNamespace, oc: OnePasswordConnect
) -> None:
    """Verify duplicate update requests do not trigger repeated writes.

    Args:
        fake_client: Mocked SDK client.
        oc: Initialized wrapper instance.
    """
    existing_item = SimpleNamespace(
        title="old-title",
        tags=["old"],
        fields=[DummyField(purpose="USERNAME", label="username", value="old-user")],
    )
    fake_client.get_item.return_value = existing_item
    fake_client.update_item.return_value = existing_item

    oc.update_item(item_id="item-1", username="new-user")
    oc.update_item(item_id="item-1", username="new-user")

    assert fake_client.get_item.call_count == 1
    assert fake_client.update_item.call_count == 1
