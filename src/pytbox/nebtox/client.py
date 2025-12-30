#!/usr/bin/env python3

from ast import Dict
import pynetbox
import requests
from typing import Literal, Dict, Any
from ..utils.response import ReturnResponse

class NetboxClient:
    def __init__(self, url: str=None, token: str=None, timeout: int=10):
        self.url = url
        self.token = token
        self.headers = {
            'Authorization': f'Token {self.token}',
            'Content-Type': 'application/json',
        }
        self.timeout = timeout
        self.pynetbox = pynetbox.api(self.url, token=self.token)

    def get_org_sites_regions(self) -> Dict[str, Any]:
        api_url = "/api/dcim/regions/"
        r = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout)
        return r.json()

    def get_dcim_region_id(self, name):
        regions = self.get_org_sites_regions()
        for region in regions['results']:
            if region['name'] == name:
                return region['id']
        return None

    def add_dcim_region(self, name, slug=None, description=None, comments=None):
        '''
        _summary_

        Returns:
            _type_: _description_
        '''
        api_url = "/api/dcim/regions/"
        
        if slug is None:
            slug = Common.get_pinyin(name)
            self.log.info(f"用户未输入 slug, 已转换为 {slug}")
    
        data = {
            "name": name,
            "slug": slug,
            # "parent": 0,
            # "description": description,
            # "comments": comments
        }
        response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
        if response.status_code == 400:
            if "already" in response.json().get('name')[0]:
                return ReturnResponse(code=2, message=f"{name} 已存在, 跳过创建", data=response.json())
            else:
                return ReturnResponse(code=1, message=f"{name} 创建失败", data=response.json())
        return ReturnResponse(code=0, message=f"{name} 创建成功!", data=response.json())

    def get_dcim_site_id(self, name):
        api_url = "/api/dcim/sites"
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout)
        for site in response.json()['results']:
            if site['name'] == name:
                return site['id']
        return None
    
    def add_or_update_org_sites_sites(self, 
                      name, 
                      slug=None, 
                      status: Literal['planned', 'staging', 'active', 'decommissioning', 'retired']='active',
                      address: str='',
                      region_name: str=None)-> ReturnResponse:
        '''
        _summary_

        Returns:
            _type_: _description_
        '''
        api_url = "/api/dcim/sites/"
        if slug is None:
            slug = Common.get_pinyin_initials(name)
            self.log.info(f"用户未输入 slug, 已转换为 {slug}")
            
        data = {
            "name": name,
            "slug": slug,
            "status": status,
            "region": self.get_dcim_region_id(region_name),
            # "group": 0,
            # "tenant": 0,
            # "facility": "string",
            # "time_zone": "string",
            # "description": "string",
            "physical_address": address,
            # "shipping_address": "string",
            # "latitude": 99,
            # "longitude": 999,
        }
        site_id = self.get_dcim_site_id(name=name)
        if site_id:
            update_response = requests.put(url=self.url + api_url + f"{site_id}/", headers=self.headers, json=data, timeout=self.timeout)
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)

        # return 
        try:
            return ReturnResponse(code=0, msg=f"{name} 已存在, 更新成功!", data=update_response.json())
        except UnboundLocalError:
            return ReturnResponse(code=0, msg=f"{name} 创建成功!", data=create_response.json())
    
    def get_dcim_location_id(self, name):
        api_url = "/api/dcim/locations"
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout)
        for location in response.json()['results']:
            if location['name'] == name:
                return location['id']
        return None
    
    def add_or_update_dcim_location(self, name, slug=None, site_name=None, status: Literal['planned', 'staging', 'active', 'decommissioning', 'retired']='active', parent_name=None):
        if slug is None:
            slug = Common.get_pinyin_initials(name)
            self.log.info(f"用户未输入 slug, 已转换为 {slug}")
            
        api_url = "/api/dcim/locations"
        data = {
            "name": name,
            "slug": slug,
            "site": self.get_dcim_site_id(name=site_name),
            "parent": self.get_dcim_location_id(name=parent_name),
            "status": status,
            # "tenant": 0,
            # "facility": "string",
            # "description": "string",
        }
        location_id = self.get_dcim_location_id(name=name)
        if location_id:
            update_response = requests.put(url=self.url + api_url + f"{location_id}/", headers=self.headers, json=data, timeout=self.timeout)
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)

        try:
            return ReturnResponse(code=0, message=f"{name} 已存在, 更新成功!", data=update_response.json())
        except UnboundLocalError:
            return ReturnResponse(code=0, message=f"{name} 创建成功!", data=create_response.json())

    def get_ipam_ipaddress_id(self, address):
        api_url = "/api/ipam/ip-addresses/"
        params = {
            "address": address
        }
        r = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=params)
        if address is None:
            return None
        elif r.json()['count'] > 1:
            raise ValueError(f"address {address} 存在多个结果")
        elif r.json()['count'] == 0:
            return None
        else:
            return r.json()['results'][0]['id']

    def add_or_update_ipam_ipaddress(self, address, status: Literal['active', 'reserved', 'deprecated', 'dhcp', 'slaac']='active'):
        data =  {
            "address": address,
            # "vrf": 0,
            # "tenant": 0,
            "status": status,
            # "role": "loopback",
            # "assigned_object_type": "string",
            # "assigned_object_id": 9223372036854776000,
            # "nat_inside": 0,
            # "dns_name": "*.o5BeHPqBWYBlKi6hL_7LVxgcqHaPIJEoUDdwMS.Mt9GE9tgIynoGLD8pXNMQc2Dl62PSrTqddJizRp-rXPJrOlAhMidHNqYOm-nZbMrZ3-ROogz49tFMVZV9oAu_FhE4FOG2Xl5.9ufJ0MZ5XQl2ltrG0KBCqBebvsPVrCMLyU4gDNkYrbzbWcirViRQYsfDkADPnL_BZgFm_FZVhwOy_0l1YgbL.RUzE0VSb1LGf.WHewtlcvp4yLRav1RuN",
            # "description": "string",
            # "comments": "string",
        }
        api_url = "/api/ipam/ip-addresses/"
        ip_address_id = self.get_ipam_ipaddress_id(address=address)
        if ip_address_id:
            update_response = requests.put(url=self.url + api_url + f"{ip_address_id}/", headers=self.headers, json=data, timeout=self.timeout)
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
        try:
            return ReturnResponse(code=0, msg=f"{address} 已存在, 更新成功!", data=update_response.json())
        except UnboundLocalError:
            # print(create_response.json())
            return ReturnResponse(code=0, msg=f"{address} 创建成功!", data=create_response.json())

    def get_ipam_prefix_id(self, prefix):
        api_url = "/api/ipam/prefixes/"
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout)
        # print(response.json())
        for prefix in response.json()['results']:
            if prefix['prefix'] == prefix:
                return prefix['id']
        return None
    
    def get_prefix_id_by_prefix(self, prefix):
        api_url = "/api/ipam/prefixes/"
        params = {
            "contains": prefix
        }
        r = requests.get(
            url=self.url + api_url, 
            headers=self.headers, 
            params=params,
            timeout=self.timeout
        )
        if r.json()["count"] > 1:
            raise ValueError(f"prefix {prefix} 存在多个结果")
        elif r.json()["count"] == 0:
            return None
        else:
            return r.json()['results'][0]['id']

    def add_or_update_ipam_prefix(self, 
                                  prefix, 
                                  status: Literal['active', 'reserved', 'deprecated', 'dhcp', 'slaac']='active', 
                                  vlan_id: int=1,
                                  description: str=None):
        data = {
            "prefix": prefix,
            "status": status,
            "description": description
        }
        api_url = "/api/ipam/prefixes/"    
        prefix_id = self.get_prefix_id_by_prefix(prefix=prefix)
        if prefix_id:
            update_response = requests.put(url=self.url + api_url + f"{prefix_id}/", headers=self.headers, json=data, timeout=self.timeout)
            return ReturnResponse(code=0, msg=f"{prefix} 已存在, 更新成功!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            return ReturnResponse(code=0, msg=f"{prefix} 创建成功!", data=create_response.json())
  
    def get_ipam_ip_range_id(self, start_address, end_address):
        api_url = "/api/ipam/ip-ranges/"
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout)
        for ip_range in response.json()['results']:
            if ip_range['start_address'] == start_address and ip_range['end_address'] == end_address:
                return ip_range['id']
        return None

    def add_or_update_ip_ranges(self, start_address, end_address, status: Literal['active', 'reserved', 'deprecated']='active', description: str=None, comments: str=None):
        data = {
            "start_address": start_address,
            "end_address": end_address,
            # "vrf": 0,
            # "tenant": 0,
            "status": status,
            # "role": 0,
            # "description": "string",
            # "comments": "string",
        }
        api_url = "/api/ipam/ip-ranges"
        ip_range_id = self.get_ipam_ip_range_id(start_address=start_address, end_address=end_address)
        if ip_range_id:
            # update_response = requests.put(url=self.url + api_url + f"{ip_range_id}", headers=self.headers, json=data, timeout=self.timeout)
            data['id'] = ip_range_id
            update_response = self.pynetbox.ipam.ip_ranges.update([data])
        else:
            create_response = self.pynetbox.ipam.ip_ranges.create(**data)
            print(create_response)
        #     create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
        try:
            return ReturnResponse(code=0, message=f"{start_address} 已存在, 更新成功!", data=update_response)
        except UnboundLocalError:
            return ReturnResponse(code=0, message=f"{start_address} 创建成功!", data=create_response)

    def get_tenants_id(self, name):
        api_url = "/api/tenancy/tenants"
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout)
        for tenant in response.json()['results']:
            if tenant['name'] == name:
                return tenant['id']
        return None

    def add_or_update_tenants(self, name, slug: str=None):

        if slug is None:
            slug = Common.get_pinyin(name)
            self.log.info(f"用户未输入 slug, 已转换为 {slug}")

        data = {
            "name": name,
            "slug": slug
        }
        api_url = "/api/tenancy/tenants"
        tenant_id = self.get_tenants_id(name=name)
        if tenant_id:
            update_response = requests.put(url=self.url + api_url + f"{tenant_id}/", headers=self.headers, json=data, timeout=self.timeout)
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
        try:
            return ReturnResponse(code=0, message=f"{name} 已存在, 更新成功!", data=update_response)
        except UnboundLocalError:
            return ReturnResponse(code=0, message=f"{name} 创建成功!", data=create_response)
    
    
    def get_manufacturer_id_by_name(self, name):
        api_url = '/api/dcim/manufacturers/'
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout)
        for manufacturer in response.json()['results']:
            if manufacturer['name'] == name:
                return manufacturer['id']
        return None
    
    def add_or_update_device_type(self, 
                                  model: Literal['ISR1100-4G', 'MS210-48FP', 'MS210-24FP', 'MR44'],
                                  slug: str=None,
                                  u_height: int=None,
                                  manufacturer: str=None
                                  ):
        
        if slug is None:
            slug = model.lower()
        
        # 优化：使用字典默认值直接映射，不再重复 if/elif 判断
        default_u_height = {
            'ISR1100-4G': 1,
            'MS210-48FP': 1,
            'MS210-24FP': 1,
            'MR44': 1
        }
        if u_height is None:
            u_height = default_u_height.get(model, 1)
        
        api_url = '/api/dcim/device-types/'
        data = {
            "model": model,
            "slug": slug,
            "u_height": u_height,
            "manufacturer": self.get_manufacturer_id_by_name(name=manufacturer)
        }
        device_type_id = self.get_device_type_id(model=model)
        if device_type_id:
            update_response = requests.put(url=self.url + api_url + f"{device_type_id}/", headers=self.headers, json=data, timeout=self.timeout)
            return ReturnResponse(code=0, msg=f"{model} 已存在, 更新成功!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            return ReturnResponse(code=0, msg=f"{model} 创建成功!", data=create_response.json())

    def get_device_type_id(self, model):
        api_url = '/api/dcim/device-types/'
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout)
        for device_type in response.json()['results']:
            if device_type['model'] == model:
                return device_type['id']
        return None

    def get_manufacturer_id(self, name):
        api_url = '/api/dcim/manufacturers/'
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout)
        for manufacturer in response.json()['results']:
            if manufacturer['name'] == name:
                return manufacturer['id']
        return None

    def add_or_update_manufacturer(self, 
                                  name: Literal['Cisco Viptela', 'Cisco Meraki', 'Cisco', 'PaloAlto'],
                                  slug: str=None
                                  ) -> ReturnResponse:
        '''
        添加或更新制造商

        Args:
            name (Literal['Cisco Viptela', 'Cisco Meraki', 'Cisco', 'PaloAlto']): 制造商名称
            slug (str, optional): 制造商 slug. Defaults to None.

        Returns:
            ReturnResponse: 返回响应对象
        '''
        
        if slug is None:
            slug = name.lower().replace(' ', '_')

        api_url = '/api/dcim/manufacturers/'
        data = {
            "name": name,
            "slug": slug,
        }
        manufacturer_id = self.get_manufacturer_id(name=name)
        if manufacturer_id:
            update_response = requests.put(url=self.url + api_url + f"{manufacturer_id}/", headers=self.headers, json=data, timeout=self.timeout)
            return ReturnResponse(code=0, msg=f"manufacturer {name} 已存在, 更新成功!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            return ReturnResponse(code=0, msg=f"manufacturer {name} 创建成功!", data=create_response.json())
    
    def get_device_id_by_name(self, name):
        api_url = '/api/dcim/devices/'
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout)
        for device in response.json()['results']:
            if device['name'] == name:
                return device['id']
        return None
    
    def get_site_id(self, name):
        api_url = '/api/dcim/sites/'
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout)
        for site in response.json()['results']:
            if site['name'] == name:
                return site['id']
        return None
    
    def get_device_id(self, name):
        api_url = '/api/dcim/devices/'
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout)
        for device in response.json()['results']:
            if device['name'] == name:
                return device['id']
        return None
    
    def get_device_type_id_by_name(self, name):
        api_url = '/api/dcim/device-types/'
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout)
        for device_type in response.json()['results']:
            if device_type['model'] == name:
                return device_type['id']
        return None
    
    def add_or_update_device(self,
                             name,
                             device_type: Literal['ISR1100-4G', 'MS210-48FP', 'MS210-24FP', 'MR44', 'MR42', 'other']='other',
                             site: str=None,
                             status: Literal['active', 'offline', 'planned', 'staged', 'failed']='active',
                             role: Literal['router', 'switch', 'wireless_ap', 'other']='other',
                             description: str=None,
                             primary_ip4: str=None,
                             latitude: float=None,
                             longitude: float=None
                        ):
        api_url = '/api/dcim/devices/'
        data = {}
        for k, v in {
            "name": name,
            "device_type": self.get_device_type_id_by_name(name=device_type),
            "role": self.get_device_role_id(name=role),
            "site": self.get_site_id(name=site),
            "description": description,
            "status": status,
            "primary_ip4": self.get_ipam_ipaddress_id(address=primary_ip4),
            "latitude": latitude,
            "longitude": longitude
        }.items():
            if v is not None:
                data[k] = v
        
        # print(data)
        device_id = self.get_device_id(name=name)
        if device_id:
            update_response = requests.put(url=self.url + api_url + f"{device_id}/", headers=self.headers, json=data, timeout=self.timeout)
            return ReturnResponse(code=0, msg=f"device {name} 已存在, 更新成功!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            return ReturnResponse(code=0, msg=f"device {name} 创建成功!", data=create_response.json())
    
    def get_device_role_id(self, name):
        api_url = '/api/dcim/device-roles/'
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout)
        for device_role in response.json()['results']:
            if device_role['name'] == name:
                return device_role['id']
        return None
    
    def add_or_update_device_role(self,
                                  name: str=None,
                                  slug: str=None,
                                  description: str=None,
                                  color: Literal['red', 'orange', 'yellow', 'green', 'blue', 'purple', 'gray', 'black']='gray',
                            ) -> ReturnResponse:
        color_map = {
            "red": "ff0000",
            "orange": "ffa500",
            "yellow": "ffff00",
            "green": "00ff00",
            "blue": "0000ff",
            "purple": "800080",
            "gray": "808080",
            "black": "000000",
        }
        
        color = color_map[color]

        if slug is None:
            slug = name.lower()
            
        api_url = '/api/dcim/device-roles/'
        data = {
            "name": name,
            "slug": slug,
            "color": color,
        }
        if description:
            data['description'] = description
        
        device_role_id = self.get_device_role_id(name=name)
        if device_role_id:
            update_response = requests.put(url=self.url + api_url + f"{device_role_id}/", headers=self.headers, json=data, timeout=self.timeout)
            return ReturnResponse(code=0, msg=f"device role {name} 已存在, 更新成功!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            return ReturnResponse(code=0, msg=f"device role {name} 创建成功!", data=create_response.json())
        
