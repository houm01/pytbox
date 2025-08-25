#!/usr/bin/env python3

from typing import Any, Literal
import requests
from ..utils.response import ReturnResponse

class Meraki:
    '''
    Meraki Client
    '''    
    def __init__(self, api_key: str=None, organization_id: str=None, timeout: int=10):
        if not api_key:
            raise ValueError("api_key is required")
        if not organization_id:
            raise ValueError("organization_id is required")
        self.base_url = 'https://api.meraki.cn/api/v1'
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json"
        }
        self.organization_id = organization_id
        self.timeout = timeout

    def get_networks(self, tags: list[str]=None) -> ReturnResponse:
        '''
        https://developer.cisco.com/meraki/api-v1/get-organization-networks/

        Args:
            tags (list): PROD STG NSO

        Returns:
            list: _description_
        '''
        params = {}
        if tags:
            params['tags[]'] = tags
        
        r = requests.get(
            f"{self.base_url}/organizations/{self.organization_id}/networks",
            headers=self.headers,
            params=params,
            timeout=self.timeout
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f"获取到 {len(r.json())} 个网络", data=r.json())
        return ReturnResponse(code=1, msg=f"获取网络失败: {r.status_code} {r.text}")

    def get_network_id_by_name(self, name: str) -> str | None:
        '''
        name 必须是唯一值，否则仅反馈第一个匹配到的 network

        Args:
            name (str): 网络名称, 是包含的关系, 例如实际 name 是 main office, 传入的 name 可以是 office

        Returns:
            str | None: 网络ID
        '''
        r = self.get_networks()
        if r.code == 0:
            for network in r.data:
                if name in network['name']:
                    return network['id']
        return None

    def get_devices(self, network_ids: Any = []) -> ReturnResponse:
        '''
        获取设备信息
        https://developer.cisco.com/meraki/api-v1/get-organization-inventory-devices/

        Args:
            network_ids (list 或 str, 可选): 可以传入网络ID的列表，也可以直接传入单个网络ID字符串。默认为空列表，表示不指定网络ID。

        Returns:
            返回示例（部分敏感信息已隐藏）:
            [
              {
                'mac': '00:00:00:00:00:00',
                'serial': 'Q3AL-****-****',
                'name': 'OFFICE-AP01',
                'model': 'MR44',
                'networkId': 'L_***************0076',
                'orderNumber': None,
                'claimedAt': '2025-02-26T02:20:00.853251Z',
                'tags': ['MR44'],
                'productType': 'wireless',
                'countryCode': 'CN',
                'details': []
              }
            ]
        '''
        
        params = {}
        if network_ids:
            if isinstance(network_ids, str):
                params['networkIds[]'] = [network_ids]
            else:
                params['networkIds[]'] = network_ids
            
        r = requests.get(
            f"{self.base_url}/organizations/{self.organization_id}/inventory/devices", 
            headers=self.headers,
            params=params,
            timeout=self.timeout
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f"获取到 {len(r.json())} 个设备", data=r.json())
        return ReturnResponse(code=1, msg=f"获取设备失败: {r.status_code} {r.text}")

    def get_device_detail(self, serial: str) -> ReturnResponse:
        '''
        获取指定序列号（serial）的 Meraki 设备详细信息

        Args:
            serial (str): 设备的序列号

        Returns:
            ReturnResponse:
                code: 0 表示成功，1 表示失败，3 表示设备未添加
                msg: 结果说明
                data: 设备详细信息，示例（部分敏感信息已隐藏）:
                {
                    'lat': 1.1,
                    'lng': 2.2,
                    'address': '(1.1, 2.2)',
                    'serial': 'Q3AL-****-****',
                    'mac': '00:00:00:00:00:00',
                    'lanIp': '10.1.1.1',
                    'tags': ['MR44'],
                    'url': 'https://n3.meraki.cn/xxx',
                    'networkId': '00000',
                    'name': 'OFFICE-AP01',
                    'details': [],
                    'model': 'MR44',
                    'firmware': 'wireless-31-1-6',
                    'floorPlanId': '00000'
                }
        '''
        r = requests.get(
            f"{self.base_url}/devices/{serial}",
            headers=self.headers,
            timeout=self.timeout
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f"获取设备详情成功: {r.json()}", data=r.json())
        elif r.status_code == 404:
            return ReturnResponse(code=3, msg=f"设备 {serial} 还未添加过", data=None)
        return ReturnResponse(code=1, msg=f"获取设备详情失败: {r.status_code} - {r.text}", data=None)

    def get_device_availabilities(self, network_id: str=None,
                                  status: Literal['online', 'offline', 'dormant', 'alerting']=None,
                                  serial: str=None) -> ReturnResponse:
        params = {}
        
        if status:
            params["statuses[]"] = status
        
        if serial:
            params["serials[]"] = serial
        
        if network_id:
            params["networkIds[]"] = network_id
            
        r = requests.get(
            url=f"{self.base_url}/organizations/{self.organization_id}/devices/availabilities", 
            headers=self.headers,
            params=params,
            timeout=self.timeout
        )
        return ReturnResponse(code=0, msg=f"获取设备健康状态成功", data=r.json())