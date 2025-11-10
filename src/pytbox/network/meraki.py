#!/usr/bin/env python3

from typing import Any, Literal
import requests
from ..utils.response import ReturnResponse


class Meraki:
    '''
    Meraki Client
    '''    
    def __init__(self, api_key: str=None, organization_id: str=None, timeout: int=10, region: Literal['global', 'china']='china'):
        if not api_key:
            raise ValueError("api_key is required")
        if not organization_id:
            raise ValueError("organization_id is required")
        if region == 'china':
            self.base_url = 'https://api.meraki.cn/api/v1'
        else:
            self.base_url = 'https://api.meraki.com/api/v1'
            
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json"
        }
        self.organization_id = organization_id
        self.timeout = timeout

    def get_organizations(self) -> ReturnResponse:
        '''
        https://developer.cisco.com/meraki/api-v1/get-organizations/
        '''
        r = requests.get(
            f"{self.base_url}/organizations",
            headers=self.headers,
            timeout=self.timeout
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f"获取组织成功", data=r.json())
        return ReturnResponse(code=1, msg=f"获取组织失败: {r.status_code} {r.text}")

    def get_api_requests(self, timespan: int=5*60) -> ReturnResponse:
        
        params = {}
        params['timespan'] = timespan
        
        r = requests.get(
            url=f"{self.base_url}/organizations/{self.organization_id}/apiRequests",
            headers=self.headers,
            params=params,
            timeout=self.timeout
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg='获取 API 请求数量成功', data=r.json())
        return ReturnResponse(code=1, msg=f"获取 API 请求失败: {r.status_code} - {r.text}", data=None)

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

    def get_device_availability(self, network_id: list=None,
                                  status: Literal['online', 'offline', 'dormant', 'alerting']=None,
                                  serial: str=None,
                                  tags: list=None,
                                  get_all: bool=False) -> ReturnResponse:
        '''
        https://developer.cisco.com/meraki/api-v1/get-organization-devices-availabilities/

        Args:
            network_id (str, optional): 如果是列表, 不能传太多 network_id
            status (Literal[&#39;online&#39;, &#39;offline&#39;, &#39;dormant&#39;, &#39;alerting&#39;], optional): _description_. Defaults to None.
            serial (str, optional): _description_. Defaults to None.
            get_all (bool, optional): _description_. Defaults to False.

        Returns:
            ReturnResponse: _description_
        '''
        params = {}
        
        if status:
            params["statuses[]"] = status
        
        if serial:
            if isinstance(serial, str):
                params["serials[]"] = [serial]
            else:
                params["serials[]"] = serial
        
        if network_id:
            if isinstance(network_id, str):
                params["networkIds[]"] = [network_id]
            else:
                params["networkIds[]"] = network_id 
        
        if tags:
            params["tags[]"] = tags
        
        # 如果需要获取所有数据，设置每页最大数量
        if get_all:
            params['perPage'] = 1000
        
        all_data = []
        url = f"{self.base_url}/organizations/{self.organization_id}/devices/availabilities"
        
        while url:
            r = requests.get(
                url=url, 
                headers=self.headers,
                params=params if url == f"{self.base_url}/organizations/{self.organization_id}/devices/availabilities" else {},
                timeout=self.timeout
            )
            
            if r.status_code != 200:
                return ReturnResponse(code=1, msg=f"获取设备健康状态失败: {r.status_code} - {r.text}", data=None)
            
            data = r.json()
            all_data.extend(data)
            
            # 如果不需要获取所有数据，只返回第一页
            if not get_all:
                return ReturnResponse(code=0, msg=f"获取设备健康状态成功，共 {len(data)} 条", data=data)
            
            # 解析 Link header 获取下一页 URL
            url = None
            link_header = r.headers.get('Link', '')
            if link_header:
                # 解析 Link header，格式如: '<url>; rel=next, <url>; rel=prev'
                for link in link_header.split(','):
                    link = link.strip()
                    if 'rel=next' in link or 'rel="next"' in link:
                        # 提取 URL (在 < > 之间)
                        url = link.split(';')[0].strip('<> ')
                        break
        
        return ReturnResponse(code=0, msg=f"获取设备健康状态成功，共 {len(all_data)} 条", data=all_data)


    def get_device_availabilities_change_history(self, network_id: str=None, serial: str=None) -> ReturnResponse:
        '''
        https://developer.cisco.com/meraki/api-v1/get-organization-devices-availabilities/

        Args:
            network_id (str, optional): _description_. Defaults to None.
            serial (str, optional): _description_. Defaults to None.

        Returns:
            ReturnResponse: _description_
        '''
        params = {}
        if network_id:
            params['networkId'] = network_id
        if serial:
            params['serial'] = serial
            
        r = requests.get(
            url=f"{self.base_url}/organizations/{self.organization_id}/devices/availabilities/changeHistory",
            headers=self.headers,
            params=params,
            timeout=self.timeout
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f"获取设备健康状态变化历史成功", data=r.json())
        return ReturnResponse(code=1, msg=f"获取设备健康状态变化历史失败: {r.status_code} - {r.text}", data=None)
    
    def reboot_device(self, serial: str) -> ReturnResponse:
        '''
        该接口 60s 只能执行一次

        Args:
            serial (str): _description_

        Returns:
            ReturnResponse: _description_
        '''
        r = requests.post(
            url=f"{self.base_url}/devices/{serial}/reboot",
            headers=self.headers,
            timeout=self.timeout
        )
        if r.status_code == 202 and r.json()['success'] == True:
            return ReturnResponse(code=0, msg=f"重启 {serial} 成功", data=r.json())

        try:
            error_msg = r.json()['error']
        except KeyError:
            error_msg = r.json()
        return ReturnResponse(code=1, msg=f"重启 {serial} 失败, 报错 {error_msg}", data=None)
    
    def get_alerts(self):
        # from datetime import datetime, timedelta
        params = {}
        params['tsStart'] = "2025-10-20T00:00:00Z"
        params['tsEnd'] = "2025-10-30T00:00:00Z"
        # # 获取昨天0:00的时间戳（秒）
        # yesterday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        # ts_start = int(yesterday.timestamp()) * 1000
        # params['tsStart'] = str(ts_start)
        # print(params)
        r = requests.get(
            url=f"{self.base_url}/organizations/{self.organization_id}/assurance/alerts",
            headers=self.headers,
            timeout=self.timeout,
            params=params
        )
        for i in r.json():
            print(i)
        # return ReturnResponse(code=0, msg="获取告警成功", data=r.json())
    
    def get_network_events(self, network_id):
        params = {}
        params['productType'] = "wireless"
        
        print(params)
        r = requests.get(
            url=f"{self.base_url}/networks/{network_id}/events",
            headers=self.headers,
            timeout=self.timeout,
            params=params
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f"获取网络事件成功", data=r.json())
        return ReturnResponse(code=1, msg=f"获取网络事件失败: {r.status_code} - {r.text}", data=None)
    
    def get_wireless_failcounter(self, network_id: str, timespan: int=5*60, serial: str=None):
        '''
        https://developer.cisco.com/meraki/api-v1/get-network-wireless-failed-connections/
        '''
        params = {}
        params['timespan'] = timespan
        if serial:
            params['serial'] = serial
            
        r = requests.get(
            url=f"{self.base_url}/networks/{network_id}/wireless/failedConnections",
            headers=self.headers,
            timeout=self.timeout,
            params=params
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f"获取无线失败连接成功", data=r.json())
        return ReturnResponse(code=1, msg=f"获取无线失败连接失败: {r.status_code} - {r.text}", data=None)

    def claim_network_devices(self, network_id: str, serials: list[str]) -> ReturnResponse:
        '''
        https://developer.cisco.com/meraki/api-v1/claim-network-devices/

        Args:
            network_id (_type_): _description_
            serials (list): _description_

        Returns:
            ReturnResponse: _description_
        '''
        new_serials = []
        already_claimed_serials = []
        
        for serial in serials:
            r = self.get_device_detail(serial=serial)
            if r.code == 0:
                already_claimed_serials.append(serial)
            elif r.code == 3:
                new_serials.append(serial)
            else:
                new_serials.append(serial)
        
        body = {
            "serials": new_serials,
            "addAtomically": True
        }
        
        r = requests.post(
            url=f"{self.base_url}/networks/{network_id}/devices/claim",
            headers=self.headers,
            json=body,
            timeout=self.timeout + 10
        )
        
        if len(already_claimed_serials) == len(serials):
            code = 0
            msg = f"All {len(already_claimed_serials)} devices are already claimed"
        elif len(already_claimed_serials) > 0:
            code = 0
            msg = f"Some {len(already_claimed_serials)} devices are already claimed"
        else:
            code = 0
            msg = f"Claim network devices successfully, claimed {len(new_serials)} devices"
        
        return ReturnResponse(code=code, msg=msg)
        
    def update_device(self, serial: str, name: str=None, tags: list=None, address: str=None, lat: float=None, lng: float=None) -> ReturnResponse:
        '''
        https://developer.cisco.com/meraki/api-v1/update-device/
        '''
        body = {}
        if name:
            body['name'] = name
        if tags:
            body['tags'] = tags
        if address:
            body['address'] = address
        if lat:
            body['lat'] = lat
        if lng:
            body['lng'] = lng
        r = requests.put(
            url=f"{self.base_url}/devices/{serial}",
            headers=self.headers,
            json=body,
            timeout=self.timeout
        )


    def update_device(self, 
                      config_template_id: str=None,
                      serial: str=None, 
                      name: str=None, 
                      tags: list=None, 
                      address: str=None,
                      lat: float=None,
                      lng: float=None,
                      switch_profile_id: str=None
                ) -> ReturnResponse:

        body = {
            "name": name,
            "tags": tags,
        }
        
        if address:
            body['address'] = address
            body["moveMapMarker"] = True
        
        if lat:
            body['Lat'] = lat
        
        if lng:
            body['Lng'] = lng

        if not switch_profile_id:
            model = self.get_device_detail(serial=serial).data.get('model')
            for switch_profile in self.get_switch_profiles(config_template_id=config_template_id).data:
                if switch_profile.get('model') == model:
                    switch_profile_id = switch_profile.get('switchProfileId')
                    body['switchProfileId'] = switch_profile_id
        else:
            body['switchProfileId'] = switch_profile_id
        
        response = requests.put(
            url=f"{self.base_url}/devices/{serial}",
            headers=self.headers,
            json=body,
            timeout=3
        )
        if response.status_code == 200:
            return ReturnResponse(code=0, msg=f"更新设备 {serial} 成功", data=response.json())
        else:
            return ReturnResponse(code=1, msg=f"更新设备 {serial} 失败: {response.status_code} - {response.text}", data=None)
    
    def get_switch_ports(self, serial: str) -> ReturnResponse:
        '''
        https://developer.cisco.com/meraki/api-v1/get-device-switch-ports/
        '''
        r = requests.get(
            url=f"{self.base_url}/devices/{serial}/switch/ports/statuses",
            headers=self.headers,
            timeout=self.timeout
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f"获取交换机端口状态成功", data=r.json())
        return ReturnResponse(code=1, msg=f"获取交换机端口状态失败: {r.status_code} - {r.text}", data=None)
    
    def get_ssids(self, network_id):
        '''
        https://developer.cisco.com/meraki/api-v1/get-network-wireless-ssids/
        '''
        r = requests.get(
            url=f"{self.base_url}/networks/{network_id}/wireless/ssids",
            headers=self.headers,
            timeout=self.timeout
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg="获取 SSID 成功", data=r.json())
        return ReturnResponse(code=1, msg=f"获取 SSID 失败: {r.status_code} - {r.text}", data=None)
    
    def get_ssid_by_number(self, network_id, ssid_number):
        '''
        https://developer.cisco.com/meraki/api-v1/get-network-wireless-ssid-by-number/
        '''
        r = requests.get(
            url=f"{self.base_url}/networks/{network_id}/wireless/ssids/{ssid_number}",
            headers=self.headers,
            timeout=self.timeout
        )
        if r.status_code == 200:
            return r.json()['name']

    def update_ssid(self, network_id, ssid_number, body):
        '''
        https://developer.cisco.com/meraki/api-v1/update-network-wireless-ssid/

        Args:
            network_id (_type_): _description_
            ssid_number (_type_): _description_

        Returns:
            _type_: _description_
        '''
        r = requests.put(
            url=f"{self.base_url}/networks/{network_id}/wireless/ssids/{ssid_number}",
            headers=self.headers,
            timeout=self.timeout,
            json=body
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f"更新 SSID 成功", data=r.json())
        return ReturnResponse(code=1, msg=f"更新 SSID 失败: {r.status_code} - {r.text}", data=None)