#!/usr/bin/env python3


from typing import Any, Dict, Optional, Union, Literal
import urllib3
urllib3.disable_warnings()
import requests
from requests.auth import HTTPBasicAuth

from .utils.response import ReturnResponse


class VMwareClient:
    """VMware vSphere Automation API 客户端。
    
    支持多种认证方式：
    1. Basic Auth - HTTP 基础认证
    2. API Key Auth - 使用会话 ID 认证
    3. Federated Identity Auth - 联合身份认证（Bearer Token）
    """
    
    def __init__(
        self,
        host: str=None,
        username: str=None,
        password: str=None,
        version: Literal['6.7', '7.0']='6.7',
        proxies: dict=None,
        verify_ssl: bool = False,
        timeout: int = 30,
    ) -> None:
        """初始化 VMware 客户端。
        
        Args:
            host: vCenter Server 主机地址（例如：https://vcenter.example.com）
            verify_ssl: 是否验证 SSL 证书
            timeout: 请求超时时间（秒）
            proxy_host: 代理服务器主机地址
            proxy_port: 代理服务器端口
            proxy_username: 代理认证用户名（可选）
            proxy_password: 代理认证密码（可选）
        """
        self.host = host
        self.username = username
        self.password = password
        self.version = version
        self.proxies = proxies
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.session_id: Optional[str] = None
    
        self.headers = {
            "vmware-api-session-id": self.get_session()
        }
 
    def get_session(self) -> str:
        """获取 VMware vSphere API 会话 ID。
        
        Returns:
            会话 ID 字符串
        """
        if self.version == '6.7':
            url = f"{self.host}/rest/com/vmware/cis/session"
        else:
            url = f"{self.host}/api/session"
   
        response = requests.post(
            url, 
            auth=HTTPBasicAuth(self.username, self.password), 
            timeout=self.timeout, 
            verify=self.verify_ssl, 
            proxies=self.proxies
        )
        
        if response.status_code == 200 or response.status_code == 201:
            # vSphere API 通常直接返回 session ID 字符串
            session_id = response.json()
            try:
                return session_id['value']
            except Exception:
                return session_id
        else:
            return f"认证失败: {response.status_code} - {response.text}"
    
    def get_vm_list(self) -> ReturnResponse:
        '''
        _summary_

        Returns:
            ReturnResponse: _description_
        '''
        if self.version == '6.7':
            url = f"{self.host}/rest/vcenter/vm"
        else:
            url = f"{self.host}/api/vcenter/vm"
        response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=False, proxies=self.proxies)
        if response.status_code == 200:
            if self.version == '6.7':
                data = response.json().get('value')
            else:
                data = response.json()
            return ReturnResponse(code=0, msg=f'成功获取到 {len(data)} 台虚拟机', data=data)
        else:
            return ReturnResponse(code=1, msg='error', data=response.json())
   
    def get_vm(self, vm_id):
        if self.version == '6.7':
            url = f"{self.host}/rest/vcenter/vm/{vm_id}"
        else:
            url = f"{self.host}/api/vcenter/vm/{vm_id}"
        response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=False, proxies=self.proxies)
        if response.status_code == 200:
            return ReturnResponse(code=0, msg='成功获取到虚拟机', data=response.json())
        else:
            return ReturnResponse(code=1, msg=f"{response.status_code}, {response.text}", data=response.json())
   
# 使用示例
if __name__ == "__main__":
    pass
    
