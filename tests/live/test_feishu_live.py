#!/usr/bin/env python3

from __future__ import annotations

import os
from datetime import datetime

import pytest

from pytbox.feishu.client import Client

pytestmark = pytest.mark.live


def _need(name: str) -> str:
    value = os.getenv(name)
    if not value:
        pytest.skip(f"missing env: {name}")
    return value


@pytest.fixture
def feishu() -> Client:
    return Client(
        app_id=_need("FEISHU_APP_ID"),
        app_secret=_need("FEISHU_APP_SECRET"),
    )


def test_live_get_tenant_access_token(feishu: Client) -> None:
    result = feishu.auth.get_tenant_access_token()
    assert result.code == 0
    assert isinstance(result.data, dict)
    assert isinstance(result.data.get("token"), str)
    assert isinstance(result.data.get("expires_at"), int)


def test_live_send_text_write(feishu: Client) -> None:
    if os.getenv("FEISHU_LIVE_ALLOW_WRITE") != "1":
        pytest.skip("set FEISHU_LIVE_ALLOW_WRITE=1 to enable write test")

    receive_id = _need("FEISHU_RECEIVE_ID")
    text = f"[live] pytbox {datetime.utcnow().isoformat()}"

    result = feishu.message.send_text(text=text, receive_id=receive_id)

    assert result.code == 0
