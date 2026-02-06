#!/usr/bin/env python3

import json
from types import SimpleNamespace
from typing import Any

from pytbox.feishu.endpoints import BitableEndpoint, ExtensionsEndpoint, MessageEndpoint
from pytbox.schemas.response import ReturnResponse


class DummyParent:
    def __init__(self, response: ReturnResponse) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def request(self, **kwargs: Any) -> ReturnResponse:
        self.calls.append(kwargs)
        return self.response


def test_webhook_send_feishu_card_uses_no_auth() -> None:
    parent = DummyParent(ReturnResponse(code=0, msg="ok", data={}))
    endpoint = MessageEndpoint(parent=parent)

    result = endpoint.webhook_send_feishu_card(
        webhook_url="https://example.com/webhook",
        template_id="tpl-1",
    )

    assert result.code == 0
    assert parent.calls[0]["use_auth"] is False
    assert parent.calls[0]["path"] == "https://example.com/webhook"


def test_upload_file_returns_return_response(tmp_path) -> None:
    parent = DummyParent(ReturnResponse(code=0, msg="ok", data={"file_key": "file-key-1"}))
    endpoint = ExtensionsEndpoint(parent=parent)
    file_path = tmp_path / "demo.txt"
    file_path.write_text("demo", encoding="utf-8")

    result = endpoint.upload_file(file_name="demo.txt", file_path=str(file_path))

    assert isinstance(result, ReturnResponse)
    assert result.code == 0
    assert result.data == {"file_key": "file-key-1"}
    assert parent.calls[0]["path"] == "/im/v1/files"


def test_send_file_uses_upload_file_return_response() -> None:
    parent = DummyParent(ReturnResponse(code=0, msg="ok", data={"message_id": "m1"}))
    parent.extensions = SimpleNamespace(
        parse_receive_id_type=lambda receive_id: "open_id",
        upload_file=lambda **kwargs: ReturnResponse(code=0, msg="ok", data={"file_key": "fk-1"}),
    )
    endpoint = MessageEndpoint(parent=parent)

    result = endpoint.send_file(file_name="demo.txt", file_path="/tmp/demo.txt", receive_id="ou_xxx")

    assert result.code == 0
    assert parent.calls[0]["path"] == "/im/v1/messages?receive_id_type=open_id"
    payload = parent.calls[0]["body"]
    parsed_content = json.loads(payload["content"])
    assert parsed_content["file_key"] == "fk-1"


def test_query_record_id_returns_return_response() -> None:
    parent = DummyParent(
        ReturnResponse(
            code=0,
            msg="ok",
            data={"items": [{"record_id": "rec-1"}]},
        )
    )
    endpoint = BitableEndpoint(parent=parent)

    result = endpoint.query_record_id(
        app_token="app",
        table_id="table",
        filter_field_name="name",
        filter_value="value",
    )

    assert isinstance(result, ReturnResponse)
    assert result.code == 0
    assert result.data["record_id"] == "rec-1"


def test_get_user_info_by_open_id_returns_return_response() -> None:
    parent = DummyParent(
        ReturnResponse(
            code=0,
            msg="ok",
            data={"user": {"name": "test-user"}},
        )
    )
    endpoint = ExtensionsEndpoint(parent=parent)

    result = endpoint.get_user_info_by_open_id(open_id="ou_xxx", get="name")

    assert isinstance(result, ReturnResponse)
    assert result.code == 0
    assert result.data == {"name": "test-user"}
