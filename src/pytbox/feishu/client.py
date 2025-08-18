#!/usr/bin/env python3

from typing import Optional, Union, Any, Dict, Type, List
from dataclasses import dataclass
from .endpoints import (
    AuthEndpoint,
    MessageEndpoint,
    ExtensionsEndpoint,
    BitableEndpoint,
    DocsEndpoint,
    CalendarEndpoint
)

from .errors import (
    RequestTimeoutError,
    is_api_error_code,
    APIResponseError,
    HTTPResponseError
)
from types import TracebackType
from abc import abstractclassmethod
import httpx
from httpx import Request, Response
from .typing import SyncAsync

@dataclass
class ClientOptions:
    auth: Optional[str] = None
    timeout_ms: int = 60_000
    base_url: str = "https://open.feishu.cn/open-apis"


@dataclass
class FeishuResponse:
    code: int
    data: dict
    chat_id: str
    message_id: str
    msg_type: str
    sender: dict
    msg: dict
    expire: int
    tenant_access_token: str


class BaseClient:

    def __init__(self,
                 app_id: str,
                 app_secret: str,
                 client: Union[httpx.Client, httpx.AsyncClient],
            ) -> None:
        
        self.app_id = app_id
        self.app_secret = app_secret

        self.options = ClientOptions()

        self._clients: List[Union[httpx.Client, httpx.AsyncClient]] = []
        self.client = client

        self.auth = AuthEndpoint(self)
        self.message = MessageEndpoint(self)
        self.bitable = BitableEndpoint(self)
        self.docs = DocsEndpoint(self)
        self.calendar = CalendarEndpoint(self)
        self.extensions = ExtensionsEndpoint(self)
        
    @property
    def client(self) -> Union[httpx.Client, httpx.AsyncClient]:
        return self._clients[-1]
    
    @client.setter
    def client(self, client: Union[httpx.Client, httpx.AsyncClient]) -> None:
        client.base_url = httpx.URL(f'{self.options.base_url}/')
        client.timeout = httpx.Timeout(timeout=self.options.timeout_ms / 1_000)
        client.headers = httpx.Headers(
            {
                "User-Agent": "cc_feishu",
            }
        )
        self._clients.append(client)


    def _build_request(self,
                       method: str,
                       path: str,
                       query: Optional[Dict[str, Any]] = None,
                       body: Optional[Dict[str, Any]] = None,
                       data: Optional[Any] = None,
                       files: Optional[Dict[str, Any]] = None,
                       token: Optional[str] = None) -> Request:
        
        headers = httpx.Headers()
        headers['Authorization'] = f'Bearer {token}'
        if 'image' in path:
            headers['Content-Type'] = 'multipart/form-data'
        
        return self.client.build_request(
            method=method, url=path, params=query, json=body, headers=headers, files=files, data=data
        )

    def _parse_response(self, response) -> Any:
        response = response.json()
        return FeishuResponse(code=response.get('code'),
                              data=response.get('data'),
                              chat_id=response.get('chat_id'),
                              message_id=response.get('message_id'),
                              msg_type=response.get('msg_type'),
                              sender=response.get('sender'),
                              msg=response.get('msg'),
                              expire=response.get('expire'),
                              tenant_access_token=response.get('tenant_access_token'))

    @abstractclassmethod
    def request(self,
                path: str,
                method: str,
                query: Optional[Dict[Any, Any]] = None,
                body: Optional[Dict[Any, Any]] = None,
                auth: Optional[str] = None,
                data: Optional[Any] = None,
                ) -> SyncAsync[Any]:
        pass


class Client(BaseClient):

    client: httpx.Client

    def __init__(self,
                 app_id: str,
                 app_secret: str,
                 client: Optional[httpx.Client]=None) -> None:
        
        if client is None:
            client = httpx.Client()
        super().__init__(app_id, app_secret, client)
    
    def __enter__(self) -> "Client":
        self.client = httpx.Client()
        self.client.__enter__()
        return self
    
    def __exit__(self,
                 exc_type: Type[BaseException],
                 exc_value: BaseException,
                 traceback: TracebackType) -> None:
        self.client.__exit__(exc_type, exc_value, traceback)
        del self._clients[-1]
    
    def close(self) -> None:
        self.client.close()

    def _get_token(self):
        if self.auth.fetch_token_from_file():
            return self.auth.fetch_token_from_file()
        else:
            self.auth.save_token_to_file()
            return self.auth.fetch_token_from_file()

    def request(self,
                path: str,
                method: str,
                query: Optional[Dict[Any, Any]] = None,
                body: Optional[Dict[Any, Any]] = None,
                files: Optional[Dict[Any, Any]] = None,
                token: Optional[str] = None,
                data: Optional[Any] = None,
                ) -> Any:

        request = self._build_request(method, path, query, body, files=files, data=data, token=self._get_token())
        try:
            response = self._parse_response(self.client.send(request))

            if 'Invalid access token for authorization' in response.msg:
                self.auth.save_token_to_file()
                request = self._build_request(method, path, query, body, files=files, data=data, token=self._get_token())
                return self._parse_response(self.client.send(request))
            else:
                return response
        except httpx.TimeoutException:
            raise RequestTimeoutError()