#!/usr/bin/env python3

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ReturnResponse:
    """统一响应格式类
    
    Attributes:
        code: 响应状态码
            0 - 成功 (SUCCESS)
            1 - 一般错误 (ERROR)
            2 - 警告 (WARNING)
            3 - 未授权 (UNAUTHORIZED)
            4 - 资源未找到 (NOT_FOUND)
            5 - 请求超时 (TIMEOUT)
            6 - 参数错误 (INVALID_PARAMS)
            7 - 权限不足 (PERMISSION_DENIED)
            8 - 服务不可用 (SERVICE_UNAVAILABLE)
            9 - 数据库错误 (DATABASE_ERROR)
            10 - 网络错误 (NETWORK_ERROR)
        msg: 响应消息描述
        data: 响应数据，可以是任意类型
    """
    code: int = 0
    msg: str = ''
    data: Optional[Any] = None
    
    def is_success(self) -> bool:
        """判断是否为成功响应
        
        Returns:
            bool: code为0时返回True，否则返回False
        """
        return self.code == 0
    
    def is_error(self) -> bool:
        """判断是否为错误响应
        
        Returns:
            bool: code不为0时返回True，否则返回False
        """
        return self.code != 0