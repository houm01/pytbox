#!/usr/bin/env python3

import time

from pytbox.feishu.client import TokenProvider
from pytbox.schemas.response import ReturnResponse


def test_token_provider_memory_cache_hit(tmp_path) -> None:
    counter = {"count": 0}

    def fetcher() -> ReturnResponse:
        counter["count"] += 1
        return ReturnResponse(
            code=0,
            msg="ok",
            data={
                "token": f"token-{counter['count']}",
                "expires_at": int(time.time()) + 3600,
            },
        )

    provider = TokenProvider(
        fetcher=fetcher,
        cache_path=str(tmp_path / "token_cache.json"),
        refresh_buffer_seconds=60,
        file_cache_enabled=True,
    )

    first = provider.get_token()
    second = provider.get_token()

    assert first.code == 0
    assert second.code == 0
    assert counter["count"] == 1
    assert second.data["token"] == "token-1"


def test_token_provider_refresh_when_expired(tmp_path) -> None:
    counter = {"count": 0}

    def fetcher() -> ReturnResponse:
        counter["count"] += 1
        return ReturnResponse(
            code=0,
            msg="ok",
            data={
                "token": f"token-{counter['count']}",
                "expires_at": int(time.time()) + 1200,
            },
        )

    provider = TokenProvider(
        fetcher=fetcher,
        cache_path=str(tmp_path / "token_cache.json"),
        refresh_buffer_seconds=60,
        file_cache_enabled=True,
    )

    first = provider.get_token()
    assert first.code == 0
    provider._memory_expires_at = int(time.time()) - 1
    provider._write_cache_file(token="stale-token", expires_at=int(time.time()) - 1)

    refreshed = provider.get_token()

    assert refreshed.code == 0
    assert counter["count"] == 2
    assert refreshed.data["token"] == "token-2"


def test_token_provider_refresh_failure_no_secret_in_logs(tmp_path, caplog) -> None:
    secret = "token-secret-value"

    def fetcher() -> ReturnResponse:
        return ReturnResponse(code=4001, msg="refresh failed", data={"token": secret})

    provider = TokenProvider(
        fetcher=fetcher,
        cache_path=str(tmp_path / "token_cache.json"),
        refresh_buffer_seconds=60,
        file_cache_enabled=True,
    )

    caplog.set_level("INFO")
    result = provider.get_token()

    assert result.code == 4001
    for record in caplog.records:
        assert secret not in record.getMessage()
