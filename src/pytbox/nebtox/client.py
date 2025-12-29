#!/usr/bin/env python3

from ast import Dict
import pynetbox
import requests
from typing import Literal, Dict, Any


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
    
    def add_or_update_dcim_site(self, 
                      name, 
                      slug=None, 
                      status: Literal['planned', 'staging', 'active', 'decommissioning', 'retired']='active',
                      address: str='',
                      region_name: str=None):
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

        try:
            return ReturnResponse(code=0, message=f"{name} 已存在, 更新成功!", data=update_response.json())
        except UnboundLocalError:
            return ReturnResponse(code=0, message=f"{name} 创建成功!", data=create_response.json())
    
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
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout)
        for ip_address in response.json()['results']:
            if ip_address['address'] == address:
                return ip_address['id']
        return None

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
            return ReturnResponse(code=0, message=f"{address} 已存在, 更新成功!", data=update_response.json())
        except UnboundLocalError:
            print(create_response.json())
            return ReturnResponse(code=0, message=f"{address} 创建成功!", data=create_response.json())

    def get_ipam_prefix_id(self, prefix):
        api_url = "/api/ipam/prefixes/"
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout)
        for prefix in response.json()['results']:
            if prefix['prefix'] == prefix:
                return prefix['id']
        return None

    def add_or_update_ipam_prefix(self, prefix, status: Literal['active', 'reserved', 'deprecated', 'dhcp', 'slaac']='active', vlan_id: int=None):
        data = {
            "prefix": prefix,
            "status": status,
        }
        api_url = "/api/ipam/prefixes/"
        prefix_id = self.get_ipam_prefix_id(prefix=prefix)
        if prefix_id:
            update_response = requests.put(url=self.url + api_url + f"{prefix_id}/", headers=self.headers, json=data, timeout=self.timeout)
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
        try:
            return ReturnResponse(code=0, message=f"{prefix} 已存在, 更新成功!", data=update_response.json())
        except UnboundLocalError:
            return ReturnResponse(code=0, message=f"{prefix} 创建成功!", data=create_response.json())

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