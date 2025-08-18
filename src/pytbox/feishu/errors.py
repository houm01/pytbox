#!/usr/bin/env python3

from enum import Enum
from typing import Optional

import httpx


class RequestTimeoutError(Exception):
    code = "notionhq_client_request_timeout"

    def __init__(self, message: str="Request to Notion API has time out") -> None:
        super().__init__(message)


class HTTPResponseError(Exception):
    def __init__(self, response: httpx.Response, message: Optional[str]=None) -> None:
        if message is None:
            message = (
                f'Request to Notion API failed with status: {response.status_code}'
            )
        super().__init__(message)

        self.status = response.status_code
        self.headers = response.headers
        self.body = response.text


class APIErrorCode(str, Enum):
    Unauthorized = "unauthorized"


class APIResponseError(HTTPResponseError):

    code: APIErrorCode

    def __init__(self, response: httpx.Response, message: str, code: APIErrorCode) -> None:
        super().__init__(response, message)
        self.code = code


def is_api_error_code(code: str) -> bool:
    if isinstance(code, str):
        return code in (error_code.value for error_code in APIErrorCode)
    return False