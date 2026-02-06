#!/usr/bin/env python3

import json
import logging
import os
import threading
import time
import uuid
from abc import abstractclassmethod
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Callable, Dict, List, Optional, Type, Union

import httpx

from ..schemas.response import ReturnResponse
from .endpoints import (
    AuthEndpoint,
    BitableEndpoint,
    CalendarEndpoint,
    DocsEndpoint,
    ExtensionsEndpoint,
    MessageEndpoint,
)
from .typing import SyncAsync

logger = logging.getLogger(__name__)


@dataclass
class ClientOptions:
    """
    ClientOptions 类。

    用于 Client Options 相关能力的封装。
    """

    auth: Optional[str] = None
    timeout_ms: int = 60_000
    base_url: str = "https://open.feishu.cn/open-apis"
    retry_max_attempts: int = 3
    retry_backoff_seconds: float = 0.5
    token_refresh_buffer_seconds: int = 300
    token_cache_path: str = "/tmp/.feishu_token.json"
    token_file_cache_enabled: bool = True


@dataclass
class FeishuResponse:
    """
    FeishuResponse 兼容数据结构（保留导出，避免历史导入报错）。
    """

    code: int
    data: Dict[str, Any]
    chat_id: Optional[str] = None
    message_id: Optional[str] = None
    msg_type: Optional[str] = None
    sender: Optional[Dict[str, Any]] = None
    msg: Optional[str] = None
    expire: Optional[int] = None
    tenant_access_token: Optional[str] = None


class TokenProvider:
    """
    统一 token 缓存/刷新入口。
    """

    def __init__(
        self,
        fetcher: Callable[[], ReturnResponse],
        cache_path: str,
        refresh_buffer_seconds: int = 300,
        file_cache_enabled: bool = True,
    ) -> None:
        self._fetcher = fetcher
        self._cache_path = cache_path
        self._refresh_buffer_seconds = refresh_buffer_seconds
        self._file_cache_enabled = file_cache_enabled
        self._memory_token: Optional[str] = None
        self._memory_expires_at: int = 0
        self._lock = threading.RLock()

    def get_token(self) -> ReturnResponse:
        """
        获取可用 token（优先内存，再落盘，最后刷新）。
        """

        with self._lock:
            task_id = uuid.uuid4().hex[:8]
            start = time.monotonic()
            now = int(time.time())

            if self._is_valid(self._memory_token, self._memory_expires_at, now):
                self._log_task(task_id, "token.memory", "hit", start)
                return ReturnResponse.ok(
                    msg="token cache hit (memory)",
                    data={
                        "token": self._memory_token,
                        "expires_at": self._memory_expires_at,
                    },
                )

            if self._file_cache_enabled:
                cached = self._read_cache_file()
                token = cached.get("token")
                expires_at = int(cached.get("expires_at", 0) or 0)
                if self._is_valid(token, expires_at, now):
                    self._memory_token = token
                    self._memory_expires_at = expires_at
                    self._log_task(task_id, "token.file", "hit", start)
                    return ReturnResponse.ok(
                        msg="token cache hit (file)",
                        data={"token": token, "expires_at": expires_at},
                    )

            refresh_resp = self.refresh()
            self._log_task(
                task_id,
                "token.refresh",
                "ok" if refresh_resp.code == 0 else "fail",
                start,
            )
            return refresh_resp

    def refresh(self) -> ReturnResponse:
        """
        强制刷新 token。
        """

        with self._lock:
            resp = self._fetcher()
            if resp.code != 0:
                return resp

            payload = resp.data if isinstance(resp.data, dict) else {}
            token = payload.get("token")
            expires_at = int(payload.get("expires_at", 0) or 0)
            if not token or not expires_at:
                return ReturnResponse.fail(
                    code=4001,
                    msg="token response invalid",
                    data={"error": {"target": "token_provider.refresh"}},
                )

            self._memory_token = token
            self._memory_expires_at = expires_at
            if self._file_cache_enabled:
                self._write_cache_file(token=token, expires_at=expires_at)

            return ReturnResponse.ok(
                msg="token refreshed",
                data={"token": token, "expires_at": expires_at},
            )

    def peek_file_token(self) -> ReturnResponse:
        """
        仅读取文件缓存，不触发刷新。
        """

        with self._lock:
            cached = self._read_cache_file()
            token = cached.get("token")
            expires_at = int(cached.get("expires_at", 0) or 0)
            if token:
                return ReturnResponse.ok(
                    msg="token cache read",
                    data={"token": token, "expires_at": expires_at},
                )
            return ReturnResponse.no_data(msg="token cache empty")

    def _is_valid(self, token: Optional[str], expires_at: int, now: int) -> bool:
        if not token or not expires_at:
            return False
        return expires_at - now > self._refresh_buffer_seconds

    def _read_cache_file(self) -> Dict[str, Any]:
        if not self._file_cache_enabled:
            return {}
        if not os.path.exists(self._cache_path):
            return {}
        try:
            with open(self._cache_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if isinstance(payload, dict):
                return payload
            return {}
        except (OSError, ValueError):
            return {}

    def _write_cache_file(self, token: str, expires_at: int) -> None:
        cache_dir = os.path.dirname(self._cache_path)
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)

        payload = {"token": token, "expires_at": expires_at}
        temp_path = f"{self._cache_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        os.replace(temp_path, self._cache_path)

    def _log_task(self, task_id: str, target: str, result: str, start: float) -> None:
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "task_id=%s target=%s result=%s duration_ms=%s",
            task_id,
            target,
            result,
            duration_ms,
        )


class BaseClient:
    """
    BaseClient 类。

    用于 Base Client 相关能力的封装。
    """

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        client: Union[httpx.Client, httpx.AsyncClient],
    ) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self.options = ClientOptions()

        self._clients: List[Union[httpx.Client, httpx.AsyncClient]] = []
        self.client = client

        self.token_provider = TokenProvider(
            fetcher=self._fetch_token_from_api,
            cache_path=self.options.token_cache_path,
            refresh_buffer_seconds=self.options.token_refresh_buffer_seconds,
            file_cache_enabled=self.options.token_file_cache_enabled,
        )

        self.auth = AuthEndpoint(self)
        self.message = MessageEndpoint(self)
        self.bitable = BitableEndpoint(self)
        self.docs = DocsEndpoint(self)
        self.calendar = CalendarEndpoint(self)
        self.extensions = ExtensionsEndpoint(self)

    @property
    def client(self) -> Union[httpx.Client, httpx.AsyncClient]:
        """
        执行 client 相关逻辑。

        Returns:
            Any: 返回值。
        """

        return self._clients[-1]

    @client.setter
    def client(self, client: Union[httpx.Client, httpx.AsyncClient]) -> None:
        """
        执行 client 相关逻辑。
        """

        client.base_url = httpx.URL(f"{self.options.base_url}/")
        client.timeout = httpx.Timeout(timeout=self.options.timeout_ms / 1_000)
        client.headers = httpx.Headers({"User-Agent": "cc_feishu"})
        self._clients.append(client)

    def _build_request(
        self,
        method: str,
        path: str,
        query: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        files: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Request:
        request_headers = httpx.Headers(headers or {})
        if token:
            request_headers["Authorization"] = f"Bearer {token}"
        return self.client.build_request(
            method=method,
            url=path,
            params=query,
            json=body,
            headers=request_headers,
            files=files,
            data=data,
        )

    def _build_success_response(
        self, response: httpx.Response, response_json: Dict[str, Any]
    ) -> ReturnResponse:
        msg = str(response_json.get("msg") or response_json.get("message") or "OK")
        data = response_json.get("data")
        if data is None:
            extra = {
                key: value
                for key, value in response_json.items()
                if key not in {"code", "msg", "message"}
            }
            data = extra or None
        return ReturnResponse(code=0, msg=msg, data=data)

    def _build_error_response(
        self, response: Optional[httpx.Response], response_json: Dict[str, Any], msg: str
    ) -> ReturnResponse:
        http_status = response.status_code if response is not None else None
        err_code = response_json.get("code", http_status or 4001)
        try:
            code = int(err_code)
        except (TypeError, ValueError):
            code = 4001
        error = {
            "http_status": http_status,
            "errcode": response_json.get("code"),
            "errmsg": response_json.get("msg") or response_json.get("errmsg") or msg,
            "req_id": response_json.get("request_id") or response_json.get("req_id"),
        }
        payload = response_json.get("data")
        if not isinstance(payload, dict):
            payload = {"raw": payload}
        payload["error"] = error
        return ReturnResponse(code=code, msg=msg, data=payload)

    def _is_retryable_status(self, status_code: int) -> bool:
        return status_code == 429 or status_code >= 500

    def _should_retry_by_api_code(self, response_json: Dict[str, Any]) -> bool:
        if not response_json:
            return False
        code = response_json.get("code")
        if isinstance(code, int):
            return code in {429, 500, 502, 503, 504}
        return False

    def _is_invalid_token(self, response_json: Dict[str, Any], msg: str) -> bool:
        code = response_json.get("code")
        if code in {99991661, 99991663, 99991668}:
            return True
        lower_msg = msg.lower()
        return "invalid access token" in lower_msg or "tenant_access_token" in lower_msg

    def _sleep_backoff(self, attempt: int) -> None:
        time.sleep(self.options.retry_backoff_seconds * (2 ** (attempt - 1)))

    def _rewind_files(self, files: Optional[Dict[str, Any]]) -> None:
        if not files:
            return
        for value in files.values():
            file_obj: Optional[Any] = None
            if hasattr(value, "seek"):
                file_obj = value
            elif isinstance(value, tuple):
                for item in value:
                    if hasattr(item, "seek"):
                        file_obj = item
                        break
            if file_obj is not None:
                try:
                    file_obj.seek(0)
                except (OSError, ValueError):
                    continue

    @abstractclassmethod
    def request(
        self,
        path: str,
        method: str,
        query: Optional[Dict[Any, Any]] = None,
        body: Optional[Dict[Any, Any]] = None,
        auth: Optional[str] = None,
        data: Optional[Any] = None,
        files: Optional[Dict[Any, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_auth: bool = True,
    ) -> SyncAsync[ReturnResponse]:
        """
        发起请求。
        """

        pass


class Client(BaseClient):
    """
    Client 类。

    用于 Client 相关能力的封装。
    """

    client: httpx.Client

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        client: Optional[httpx.Client] = None,
    ) -> None:
        if client is None:
            client = httpx.Client()
        super().__init__(app_id, app_secret, client)

    def __enter__(self) -> "Client":
        self.client = httpx.Client()
        self.client.__enter__()
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException],
        exc_value: BaseException,
        traceback: TracebackType,
    ) -> None:
        self.client.__exit__(exc_type, exc_value, traceback)
        del self._clients[-1]

    def close(self) -> None:
        self.client.close()

    def _get_token(self) -> ReturnResponse:
        return self.token_provider.get_token()

    def _fetch_token_from_api(self) -> ReturnResponse:
        payload = {"app_id": self.app_id, "app_secret": self.app_secret}
        response = self.request(
            path="/auth/v3/tenant_access_token/internal",
            method="POST",
            body=payload,
            use_auth=False,
        )
        if response.code != 0:
            return response

        token_payload = response.data if isinstance(response.data, dict) else {}
        token = token_payload.get("tenant_access_token")
        expire_seconds = int(token_payload.get("expire", 0) or 0)
        if not token or expire_seconds <= 0:
            return ReturnResponse.fail(
                code=4001,
                msg="failed to parse tenant access token",
                data={"error": {"target": "auth.fetch_token"}},
            )
        expires_at = int(time.time()) + expire_seconds
        return ReturnResponse.ok(
            msg="token fetched",
            data={"token": token, "expires_at": expires_at},
        )

    def request(
        self,
        path: str,
        method: str,
        query: Optional[Dict[Any, Any]] = None,
        body: Optional[Dict[Any, Any]] = None,
        auth: Optional[str] = None,
        data: Optional[Any] = None,
        files: Optional[Dict[Any, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_auth: bool = True,
    ) -> ReturnResponse:
        task_id = uuid.uuid4().hex[:8]
        start = time.monotonic()
        request_target = f"{method.upper()} {path}"
        refreshed_once = False

        token: Optional[str] = None
        if use_auth:
            token_resp = self._get_token()
            if token_resp.code != 0:
                duration_ms = int((time.monotonic() - start) * 1000)
                logger.warning(
                    "task_id=%s target=%s result=token_fail duration_ms=%s",
                    task_id,
                    request_target,
                    duration_ms,
                )
                return token_resp
            token_data = token_resp.data if isinstance(token_resp.data, dict) else {}
            token = token_data.get("token")

        last_error: Optional[ReturnResponse] = None
        for attempt in range(1, self.options.retry_max_attempts + 1):
            self._rewind_files(files)
            request = self._build_request(
                method=method,
                path=path,
                query=query,
                body=body,
                data=data,
                files=files,
                token=auth or token,
                headers=headers,
            )

            try:
                response = self.client.send(request)
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                retryable = attempt < self.options.retry_max_attempts
                if retryable:
                    self._sleep_backoff(attempt)
                    continue
                last_error = ReturnResponse.fail(
                    code=4001,
                    msg=str(exc.__class__.__name__),
                    data={"error": {"target": request_target}},
                )
                break

            response_json: Dict[str, Any]
            try:
                response_json = response.json()
                if not isinstance(response_json, dict):
                    response_json = {"data": response_json}
            except ValueError:
                response_json = {}

            msg = str(
                response_json.get("msg")
                or response_json.get("errmsg")
                or response.reason_phrase
                or "request failed"
            )

            if use_auth and self._is_invalid_token(response_json, msg) and not refreshed_once:
                refresh_resp = self.token_provider.refresh()
                refreshed_once = True
                if refresh_resp.code == 0:
                    refresh_data = (
                        refresh_resp.data if isinstance(refresh_resp.data, dict) else {}
                    )
                    token = refresh_data.get("token")
                    continue
                last_error = refresh_resp
                break

            api_code = response_json.get("code", 0 if response.status_code < 400 else response.status_code)
            try:
                api_code_int = int(api_code)
            except (TypeError, ValueError):
                api_code_int = 4001

            is_success = response.status_code < 400 and api_code_int == 0
            if is_success:
                result = self._build_success_response(response=response, response_json=response_json)
                duration_ms = int((time.monotonic() - start) * 1000)
                logger.info(
                    "task_id=%s target=%s result=ok duration_ms=%s",
                    task_id,
                    request_target,
                    duration_ms,
                )
                return result

            retryable = (
                self._is_retryable_status(response.status_code)
                or self._should_retry_by_api_code(response_json)
            )
            error_resp = self._build_error_response(
                response=response,
                response_json=response_json,
                msg=msg,
            )
            last_error = error_resp
            if retryable and attempt < self.options.retry_max_attempts:
                self._sleep_backoff(attempt)
                continue
            break

        duration_ms = int((time.monotonic() - start) * 1000)
        logger.warning(
            "task_id=%s target=%s result=fail duration_ms=%s",
            task_id,
            request_target,
            duration_ms,
        )
        if last_error is not None:
            return last_error
        return ReturnResponse.fail(
            code=4001,
            msg="unknown request failure",
            data={"error": {"target": request_target}},
        )
