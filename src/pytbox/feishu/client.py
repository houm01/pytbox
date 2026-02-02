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
    """
    ClientOptions 类。

    用于 Client Options 相关能力的封装。
    """
    auth: Optional[str] = None
    timeout_ms: int = 60_000
    base_url: str = "https://open.feishu.cn/open-apis"


@dataclass
class FeishuResponse:
    """
    FeishuResponse 类。

    用于 Feishu Response 相关能力的封装。
    """
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

    """
    BaseClient 类。

    用于 Base Client 相关能力的封装。
    """
    def __init__(self,
                 app_id: str,
                 app_secret: str,
                 client: Union[httpx.Client, httpx.AsyncClient],
            ) -> None:
        
        """
        初始化对象。

        Args:
            app_id: 资源 ID。
            app_secret: app_secret 参数。
            client: client 参数。
        """
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

        Args:
            client: client 参数。

        Returns:
            Any: 返回值。
        """
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
        
        """
        执行 build request 相关逻辑。

        Args:
            method: method 参数。
            path: path 参数。
            query: query 参数。
            body: body 参数。
            data: data 参数。
            files: files 参数。
            token: token 参数。

        Returns:
            Any: 返回值。
        """
        headers = httpx.Headers()
        headers['Authorization'] = f'Bearer {token}'
        if 'image' in path:
            headers['Content-Type'] = 'multipart/form-data'
        
        return self.client.build_request(
            method=method, url=path, params=query, json=body, headers=headers, files=files, data=data
        )

    def _parse_response(self, response) -> Any:
        """
        执行 parse response 相关逻辑。

        Args:
            response: response 参数。

        Returns:
            Any: 返回值。
        """
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
        """
        发起请求。

        Args:
            path: path 参数。
            method: method 参数。
            query: query 参数。
            body: body 参数。
            auth: auth 参数。
            data: data 参数。

        Returns:
            Any: 返回值。
        """
        pass


class Client(BaseClient):

    """
    Client 类。

    用于 Client 相关能力的封装。
    """
    client: httpx.Client

    def __init__(self,
                 app_id: str,
                 app_secret: str,
                 client: Optional[httpx.Client]=None) -> None:
        
        """
        初始化对象。

        Args:
            app_id: 资源 ID。
            app_secret: app_secret 参数。
            client: client 参数。
        """
        if client is None:
            client = httpx.Client()
        super().__init__(app_id, app_secret, client)
    
    def __enter__(self) -> "Client":
        """
        进入上下文管理器。

        Returns:
            Any: 返回值。
        """
        self.client = httpx.Client()
        self.client.__enter__()
        return self
    
    def __exit__(self,
                 exc_type: Type[BaseException],
                 exc_value: BaseException,
                 traceback: TracebackType) -> None:
        """
        退出上下文管理器并做资源清理。

        Args:
            exc_type: exc_type 参数。
            exc_value: exc_value 参数。
            traceback: traceback 参数。

        Returns:
            Any: 返回值。
        """
        self.client.__exit__(exc_type, exc_value, traceback)
        del self._clients[-1]
    
    def close(self) -> None:
        """
        关闭。

        Returns:
            Any: 返回值。
        """
        self.client.close()

    def _get_token(self):
        """
        执行 get token 相关逻辑。

        Returns:
            Any: 返回值。
        """
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

        """
        发起请求。

        Args:
            path: path 参数。
            method: method 参数。
            query: query 参数。
            body: body 参数。
            files: files 参数。
            token: token 参数。
            data: data 参数。

        Returns:
            Any: 返回值。
        """
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
