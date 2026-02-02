#!/usr/bin/env python3

from enum import Enum
from typing import Optional

import httpx


class RequestTimeoutError(Exception):
    """
    RequestTimeoutError 类。

    用于 Request Timeout Error 相关能力的封装。
    """
    code = "notionhq_client_request_timeout"

    def __init__(self, message: str="Request to Notion API has time out") -> None:
        """
        初始化对象。

        Args:
            message: message 参数。
        """
        super().__init__(message)


class HTTPResponseError(Exception):
    """
    HTTPResponseError 类。

    用于 HTTP Response Error 相关能力的封装。
    """
    def __init__(self, response: httpx.Response, message: Optional[str]=None) -> None:
        """
        初始化对象。

        Args:
            response: response 参数。
            message: message 参数。
        """
        if message is None:
            message = (
                f'Request to Notion API failed with status: {response.status_code}'
            )
        super().__init__(message)

        self.status = response.status_code
        self.headers = response.headers
        self.body = response.text


class APIErrorCode(str, Enum):
    """
    APIErrorCode 类。

    用于 API Error Code 相关能力的封装。
    """
    Unauthorized = "unauthorized"


class APIResponseError(HTTPResponseError):

    """
    APIResponseError 类。

    用于 API Response Error 相关能力的封装。
    """
    code: APIErrorCode

    def __init__(self, response: httpx.Response, message: str, code: APIErrorCode) -> None:
        """
        初始化对象。

        Args:
            response: response 参数。
            message: message 参数。
            code: code 参数。
        """
        super().__init__(response, message)
        self.code = code


def is_api_error_code(code: str) -> bool:
    """
    判断是否api error code。

    Args:
        code: code 参数。

    Returns:
        bool: 是否满足条件。
    """
    if isinstance(code, str):
        return code in (error_code.value for error_code in APIErrorCode)
    return False
