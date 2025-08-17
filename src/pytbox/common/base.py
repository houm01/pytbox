"""
Base classes and common utilities
"""

from ..utils.timeutils import TimeUtils
from typing import Dict, Any
import json


class BaseAPI:
    """API基类，提供通用功能"""
    
    def __init__(self, base_url: str = ""):
        self.base_url = base_url
        self._session_created_at = TimeUtils.get_timestamp()
    
    def get_session_age(self) -> int:
        """获取会话存活时间（秒）"""
        current_time = TimeUtils.get_timestamp()
        return current_time - self._session_created_at
    
    def log_request(self, method: str, url: str, data: Dict[Any, Any] = None) -> str:
        """记录请求日志"""
        timestamp = TimeUtils.get_timestamp()
        log_entry = {
            "timestamp": timestamp,
            "method": method,
            "url": url,
            "data": data or {}
        }
        return json.dumps(log_entry, ensure_ascii=False)


class BaseResponse:
    """响应基类"""
    
    def __init__(self, data: Dict[Any, Any]):
        self.data = data
        self.created_at = TimeUtils.get_timestamp()
        
    def is_expired(self, ttl_seconds: int = 3600) -> bool:
        """检查响应是否过期"""
        current_time = TimeUtils.get_timestamp()
        return (current_time - self.created_at) > ttl_seconds
