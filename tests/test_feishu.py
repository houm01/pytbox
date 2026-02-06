#!/usr/bin/env python3

from pytbox.feishu.client import Client
from pytbox.schemas.response import ReturnResponse


def test_parse_message_card_elements_extracts_text() -> None:
    client = Client(app_id="app-id", app_secret="app-secret")
    elements = [
        [{"tag": "text", "text": "hello"}],
        {"content": [{"tag": "text", "text": " world"}]},
    ]
    parsed = client.extensions.parse_message_card_elements(elements)
    assert parsed == "hello world"


def test_send_message_notify_returns_return_response(monkeypatch) -> None:
    client = Client(app_id="app-id", app_secret="app-secret")

    def fake_send_card(**kwargs) -> ReturnResponse:
        return ReturnResponse(code=0, msg="ok", data=kwargs)

    monkeypatch.setattr(client.message, "send_card", fake_send_card)
    result = client.extensions.send_message_notify(title="test")
    assert isinstance(result, ReturnResponse)
    assert result.code == 0
