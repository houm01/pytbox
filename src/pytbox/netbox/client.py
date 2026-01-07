#!/usr/bin/env python3

import time
import json
import pynetbox
from typing import Literal, Dict, Any

import requests
from pypinyin import pinyin, lazy_pinyin

from ..utils.response import ReturnResponse
from ..utils.parse import Parse



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

    def get_update_comments(self, source: str=''):
        return f"""Updated by automation script\nDate: {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}\nSource: {source}"""

    def get_org_sites_regions(self) -> Dict[str, Any]:
        api_url = "/api/dcim/regions/"
        r = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout)
        return r.json()

    def get_region_id(self, name):
        api_url = "/api/dcim/regions/"
        params = {
            "name": name
        }
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=params)
        if name is None:
            return None
        if response.json()['count'] > 1:
            raise ValueError(f"region {name} 存在多个结果")
        elif response.json()['count'] == 0:
            return None
        else:
            return response.json()['results'][0]['id']

    def add_or_update_region(self, name, slug=None):
        '''
        _summary_

        Returns:
            _type_: _description_
        '''
        api_url = "/api/dcim/regions/"
        
        if slug is None:
            slug = self._process_slug(name)

        data = {
            "name": name,
            "slug": slug,
            
        }
        region_id = self.get_region_id(name=name)
        if region_id:
            update_response = requests.put(url=self.url + api_url + f"{region_id}/", headers=self.headers, json=data, timeout=self.timeout)
            if update_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"{name} 更新失败! {update_response.json()}", data=update_response.json())
            else:
                return ReturnResponse(code=0, msg=f"{name} 已存在, 更新成功!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            if create_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"{name} 创建失败! {create_response.json()}", data=create_response.json())
            else:
                return ReturnResponse(code=0, msg=f"{name} 创建成功!", data=create_response.json())

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
                      region: str=None,
                      tenant: str=None,
                      facility: str=None,
                      latitude: float=None,
                      longitude: float=None,
                      time_zone: str='Asia/Shanghai',
                      tags: dict=None
                    )-> ReturnResponse:
        '''
        _summary_

        Returns:
            _type_: _description_
        '''
        api_url = "/api/dcim/sites/"
        
        if slug:
            slug = self._process_slug(slug)
        data = {
            "name": name,
            "slug": slug,
            "status": status,
            "facility": str(facility),
            "region": self.get_region_id(region),
            "tenant": self.get_tenant_id(tenant),
            "tags": [tags],
            # "group": 0,
            "time_zone": time_zone,
            # "description": "string",
            "physical_address": address,
            # "shipping_address": "string",
            "latitude": round(float(latitude), 2) if latitude is not None else None,
            "longitude": round(float(longitude), 2) if longitude is not None else None,
        }
        data = Parse.remove_dict_none_value(data)
        site_id = self.get_site_id(name=name)
        if site_id:
            update_response = requests.put(url=self.url + api_url + f"{site_id}/", headers=self.headers, json=data, timeout=self.timeout)
            if update_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"{name} 更新失败! {update_response.json()}", data=update_response.json())
            else:
                return ReturnResponse(code=0, msg=f"{name} 已存在, 更新成功!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            if create_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"{name} 创建失败! {create_response.json()}", data=create_response.json())
            else:
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

    def get_tenants_id(self, name):
        api_url = "/api/tenancy/tenants"
        params = {
            "name": name
        }
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=params)
        if response.json()['count'] > 1:
            raise ValueError(f"tenant {name} 存在多个结果")
        elif response.json()['count'] == 0:
            return None
        else:
            return response.json()['results'][0]['id']

    def assign_ipaddress_to_interface(self, address: str, device: str, interface_name: str) -> ReturnResponse:
        api_url = "/api/ipam/ip-addresses/"
        data = {
            "address": address,
            "assigned_object_type": "dcim.interface",
            "assigned_object_id": self.get_interface_id(device=device, name=interface_name),
        }
        ipaddress_id = self.get_ipam_ipaddress_id(address=address)
        response = requests.put(url=self.url + api_url + f"{ipaddress_id}/", headers=self.headers, json=data, timeout=self.timeout)
        if response.status_code > 210:
            return ReturnResponse(code=1, msg=f"{address} 分配失败! {response.json()}", data=response.json())
        else:
            return ReturnResponse(code=0, msg=f"{address} 分配成功!", data=response.json())

    def add_or_update_ipam_ipaddress(self, 
                                     address, 
                                     status: Literal['active', 'reserved', 'deprecated', 'dhcp', 'slaac']='active',
                                     tenant: str=None,
                                     ip_type: Literal['BGP', '电信', '联通', '移动', 'Other']=None,
                                     description: str=None,
                                     assigned_object_type: Literal['dcim.interface']=None,
                                     assigned_object_id: int=None
                                    ):

        data =  {
            "address": address,
            "tenant": self.get_tenants_id(name=tenant),
            "status": status,
            "description": description,
            "assigned_object_type": assigned_object_type,
            "assigned_object_id": assigned_object_id,
        }
        if ip_type:
            
            if ip_type == 'BGP':
                color = 'ff0000'
                slug = 'bgp'
            elif ip_type == '电信':
                color = '00ff00'
                slug = 'china_telecom'
            elif ip_type == '联通':
                color = '0000ff'
                slug = 'china_unicom'
            elif ip_type == '移动':
                color = 'ffff00'
                slug = 'china_mobile'
            elif ip_type == '内网':
                color = '0000ff'
                slug = 'intranet'
            else:
                color = '808080'
                slug = 'other'
                
            data['tags'] = []
            
            data['tags'].append({
                "name": ip_type,
                "slug": slug,
                # "color": "c5d40a"
            })
        data = Parse.remove_dict_none_value(data=data)
        api_url = "/api/ipam/ip-addresses/"
        ip_address_id = self.get_ipam_ipaddress_id(address=address)
        if ip_address_id:
            update_response = requests.put(url=self.url + api_url + f"{ip_address_id}/", headers=self.headers, json=data, timeout=self.timeout)
            if update_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"{address} 更新失败! {update_response.json()}", data=update_response.json())
            else:
                return ReturnResponse(code=0, msg=f"{address} 已存在, 更新成功!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            if create_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"{address} 创建失败! {create_response.json()}", data=create_response.json())
            else:
                return ReturnResponse(code=0, msg=f"{address} 创建成功!", data=create_response.json())

    def get_ipam_prefix_id(self, prefix):
        api_url = "/api/ipam/prefixes/"
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout)
        for prefix in response.json()['results']:
            if prefix['prefix'] == prefix:
                return prefix['id']
        return None
    
    def get_prefix_id_by_prefix(self, prefix):
        api_url = "/api/ipam/prefixes/"
        params = {
            "prefix": prefix
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
                                  description: str=None,
                                  tenant: str=None
                                ):
        data = {
            "prefix": prefix,
            "status": status,
            "description": description,
            "tenant": self.get_tenants_id(name=tenant)
        }
        data = Parse.remove_dict_none_value(data)
        api_url = "/api/ipam/prefixes/"    
        prefix_id = self.get_prefix_id_by_prefix(prefix=prefix)
        if prefix_id:
            update_response = requests.put(url=self.url + api_url + f"{prefix_id}/", headers=self.headers, json=data, timeout=self.timeout)
            if update_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"{prefix} 更新失败! {update_response.json()}", data=update_response.json())
            else:
                return ReturnResponse(code=0, msg=f"{prefix} 已存在, 更新成功!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            if create_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"{prefix} 创建失败! {create_response.json()}", data=create_response.json())
            else:
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
            # print(create_response)
        #     create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
        try:
            return ReturnResponse(code=0, message=f"{start_address} 已存在, 更新成功!", data=update_response)
        except UnboundLocalError:
            return ReturnResponse(code=0, message=f"{start_address} 创建成功!", data=create_response)

    def get_tenants_id(self, name):
        api_url = "/api/tenancy/tenants"
        params = {
            "name": name
        }
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=params)
        if response.json()['count'] > 1:
            raise ValueError(f"tenant {name} 存在多个结果")
        elif response.json()['count'] == 0:
            return None
        else:
            return response.json()['results'][0]['id']

    def add_or_update_tenants(self, name, slug: str=None) -> ReturnResponse:
        '''
        添加或更新租户, requests 会有问题, 添加时提示成功，但实际没有添加，所以用了 pynetbox 模块

        Args:
            name (str): 租户名称
            slug (str, optional): _description_. Defaults to None.

        Returns:
            ReturnResponse: 返回响应对象
        '''
        if slug is None:
            slug = self._process_slug(name=name)

        data = {
            "name": name,
            "slug": slug
        }
        tenant_id = self.get_tenants_id(name=name)
        if tenant_id:
            data['id'] = tenant_id
            try:
                r = self.pynetbox.tenancy.tenants.update([data])
                action = 'update'
            except pynetbox.core.query.RequestError as e:
                return ReturnResponse(code=1, msg=f"[{action}] tenant [{name}], slug [{slug}] failed! {e}", data=None)
        else:
            try:
                r = self.pynetbox.tenancy.tenants.create(data)
                action = 'create'
            except pynetbox.core.query.RequestError as e:
                return ReturnResponse(code=1, msg=f"create tenant [{name}], slug [{slug}] failed! {e}", data=None)
        return ReturnResponse(code=0, msg=f"[{action}] tenant [{name}], slug [{slug}] success!", data=r)
    
    def _process_slug(self, name):
        slug_mapping = {
            "联想": "Lenovo",
            "群晖": "Synology",
            "锐捷": "Ruijie",
            "创旗": "trunkey",
            "创旗 TSDS-600": "trunkey_tsds_600",
            "espace_iad132e": "espace_iad132e",
            "磁带库": "tape_library",
            "行为管理": "ac",
            "路由器": "router",
            "交换机": "switch",
            "防火墙": "firewall",
            "存储": "storage",
            "其他": "other",
            "打印机": "printer",
            "服务器": "server",
            "无线控制器": "wireless_ac",
            "待补充": "other",
            "备案系统": "icp_system",
            "其他": "other",
            "堡垒机": "bastion_host",
            "负载均衡": "load_balancer",
            "客户": "customer",
            "运维": "devops",
            "供应商": "vendor"
        }
        slug = slug_mapping.get(name, None)
        if slug is None:
            # slug = lazy_pinyin(name, style=Style.NORMAL)
            slug = ''.join(lazy_pinyin(name))
        return slug.lower().replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '').replace('（', '').replace('）', '').replace('+','').replace('’', '').replace("'", "")
    
    def _process_gps(self, value):
        value = value.replace('\u200c\u200c', '')
        return round(float(value), 2) if value is not None else None
    
    def get_manufacturer_id_by_name(self, name):
        api_url = '/api/dcim/manufacturers/'
        params = {
            "name": name
        }
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=params)
        if response.json()['count'] > 1:
            raise ValueError(f"manufacturer {name} 存在多个结果")
        elif response.json()['count'] == 0:
            return None
        else:
            return response.json()['results'][0]['id']
    
    def add_or_update_device_type(self, 
                                  model: Literal['ISR1100-4G', 'MS210-48FP', 'MS210-24FP', 'MR44'],
                                  slug: str=None,
                                  u_height: int=None,
                                  manufacturer: str=None
                                  ):
        
        if slug is None:
            slug = self._process_slug(name=model)
        
        # print(slug)
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
        # print(data)
        device_type_id = self.get_device_type_id(model=model)
        if device_type_id:
            update_response = requests.put(url=self.url + api_url + f"{device_type_id}/", headers=self.headers, json=data, timeout=self.timeout)
            if update_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"{model} 更新失败! {update_response.json()}", data=update_response.json())
            else:
                return ReturnResponse(code=0, msg=f"{model} 已存在, 更新成功!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            if create_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"{model} 创建失败! {create_response.json()}", data=create_response.json())
            else:
                return ReturnResponse(code=0, msg=f"{model} 创建成功!", data=create_response.json())

    def get_device_type_id(self, model):
        api_url = '/api/dcim/device-types/'
        params = {
            "model": model
        }
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=params)
        if response.json()['count'] > 1:
            raise ValueError(f"device type {model} 存在多个结果")
        elif response.json()['count'] == 0:
            return None
        else:
            return response.json()['results'][0]['id']

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
            slug = self._process_slug(name=name)

        api_url = '/api/dcim/manufacturers/'
        data = {
            "name": name,
            "slug": slug,
        }
        manufacturer_id = self.get_manufacturer_id(name=name)
        if manufacturer_id:
            update_response = requests.put(url=self.url + api_url + f"{manufacturer_id}/", headers=self.headers, json=data, timeout=self.timeout)
            if update_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"manufacturer {name} 更新失败! {update_response.json()}", data=update_response.json())
            else:   
                return ReturnResponse(code=0, msg=f"manufacturer {name} 已存在, 更新成功!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            if create_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"manufacturer {name} 创建失败! {create_response.json()}", data=create_response.json())
            else:
                return ReturnResponse(code=0, msg=f"manufacturer {name} 创建成功!", data=create_response.json())
    
    def get_device_id_by_name(self, name):
        api_url = '/api/dcim/devices/'
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout)
        for device in response.json()['results']:
            if device['name'] == name:
                return device['id']
        return None
    
    def get_tenant_id(self, name):
        api_url = '/api/tenancy/tenants/'
        params = {
            "name": name
        }
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=params)
        if name is None:
            return None
        elif response.json()['count'] > 1:
            raise ValueError(f"tenant {name} 存在多个结果")
        elif response.json()['count'] == 0:
            return None
        else:
            return response.json()['results'][0]['id']
    
    def get_site_id(self, name):
        api_url = '/api/dcim/sites/'
        params = {
            "name": name
        }
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=params)
        for site in response.json()['results']:
            if site['name'] == name:
                return site['id']
        return None
    
    def get_device_id(self, name: str=None, tenant_id: str=None):
        api_url = '/api/dcim/devices/'
        params = {
            "name": name,
            "tenant_id": tenant_id
        }
        params = Parse.remove_dict_none_value(params)
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=params)
        if response.json()['count'] > 1:
            raise ValueError(f"device {name} 存在多个结果")
        elif response.json()['count'] == 0:
            return None
        else:
            return response.json()['results'][0]['id']
    
    def get_device_type_id_by_name(self, name):
        if name is not None:
            api_url = '/api/dcim/device-types/'
            params = {
                "model": name
            }
            response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=params)
            # print(response.json())
            if response.json()['count'] > 1:
                raise ValueError(f"device type {name} 存在多个结果")
            elif response.json()['count'] == 0 or name is None:
                return self.get_device_type_id_by_name(name='other')
                # return 'other'
            else:
                return response.json()['results'][0]['id']
        return self.get_device_type_id_by_name(name='other')
    
    def add_or_update_device(self,
                             name,
                             device_type: Literal['ISR1100-4G', 'MS210-48FP', 'MS210-24FP', 'MR44', 'MR42', 'other']='other',
                             site: str=None,
                             status: Literal['active', 'offline', 'planned', 'staged', 'failed']='active',
                             role: Literal['router', 'switch', 'wireless_ap', 'other']='other',
                             description: str=None,
                             primary_ip4: str=None,
                             latitude: float=None,
                             longitude: float=None,
                             rack: str=None,
                             tenant: str=None,
                             serial: str=None,
                             face: Literal['front', 'rear']='front',
                             position: int=None,
                             comments: str=None,
                             software_version: str=None,
                        ):
        api_url = '/api/dcim/devices/'
        data = {
            "name": name,
            "device_type": self.get_device_type_id_by_name(name=device_type),
            "role": self.get_device_role_id(name=role),
            "site": self.get_site_id(name=site),
            "description": description,
            "status": status,
            "primary_ip4": self.get_ipam_ipaddress_id(address=primary_ip4),
            "latitude": self._process_gps(value=latitude),
            "longitude": self._process_gps(value=longitude),
            "rack": self.get_rack_id(name=rack, tenant=tenant),
            "tenant": self.get_tenant_id(name=tenant),
            "serial": serial,
            "face": face,
            "position": position,
            "comments": comments,
        }
        if software_version:
            data['custom_fields'] = {}
            data['custom_fields']['SoftwareVersion'] = software_version
        data = Parse.remove_dict_none_value(data=data)
        device_id = self.get_device_id(name=name, tenant_id=self.get_tenant_id(name=tenant))

        if device_id:
            update_response = requests.put(url=self.url + api_url + f"{device_id}/", headers=self.headers, json=data, timeout=self.timeout)
            if update_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"device {name} exists, updated failed! {update_response.json()}", data=update_response.json())
            else:
                return ReturnResponse(code=0, msg=f"device {name} exists, updated successfully!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            if create_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"device {name} created failed! {create_response.json()}", data=create_response.json())
            else:
                return ReturnResponse(code=0, msg=f"device {name} created successfully!", data=create_response.json())
    
    def set_primary_ip4_to_device(self, device_name, tenant, primary_ip4):
        api_url = '/api/dcim/devices/'
        data = {
            "name": device_name,
            "tenant": tenant,
            "primary_ip4": self.get_ipam_ipaddress_id(address=primary_ip4)
        }
        device_id = self.get_device_id(name=device_name, tenant_id=self.get_tenant_id(name=tenant))
        if device_id:
            response = requests.put(url=self.url + api_url + f"{device_id}/", headers=self.headers, json=data, timeout=self.timeout)
            if response.status_code > 210:
                return ReturnResponse(code=1, msg=f"device {device_name} 更新失败! {response.json()}", data=response.json())
            else:
                return ReturnResponse(code=0, msg=f"device {device_name} 已存在, 更新成功!", data=response.json())
        else:
            return ReturnResponse(code=1, msg=f"device {device_name} 不存在!", data=None)
    
    def get_device_role_id(self, name):
        api_url = '/api/dcim/device-roles/'
        params = {
            "name": name
        }
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=params)
        if response.json()['count'] > 1:
            raise ValueError(f"device role {name} 存在多个结果")
        elif response.json()['count'] == 0:
            return None
        else:
            return response.json()['results'][0]['id']
    
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
            slug = self._process_slug(name=name)
            
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
            if update_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"device role {name} 更新失败! {update_response.json()}", data=update_response.json())
            else:
                return ReturnResponse(code=0, msg=f"device role {name} 已存在, 更新成功!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            if create_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"device role {name} 创建失败! {create_response.json()}", data=create_response.json())
            else:
                return ReturnResponse(code=0, msg=f"device role {name} 创建成功!", data=create_response.json())
    
    def get_contact_id(self, name):
        api_url = '/api/tenancy/contacts/'
        parms = {
            "name": name
        }
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=parms)
        if response.json()['count'] > 1:
            raise ValueError(f"contact {name} 存在多个结果")
        elif response.json()['count'] == 0:
            return None
        else:
            return response.json()['results'][0]['id']
    
    def add_or_update_contacts(self, 
                               name: str=None, 
                               email: str=None,
                               phone: str=None, 
                               id_card: str=None, 
                               description: str=None):
        api_url = '/api/tenancy/contacts/'
        data = Parse.remove_dict_none_value({
            "name": name,
            "email": email,
            "phone": phone,
            "description": description,
            "custom_fields": {
                "id_card": id_card,
            }
        })
        contact_id = self.get_contact_id(name=name)
        if contact_id:
            update_response = requests.put(url=self.url + api_url + f"{contact_id}/", headers=self.headers, json=data, timeout=self.timeout)
            if update_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"contact [{name}] 更新失败! {update_response.json()}", data=update_response.json())
            else:
                return ReturnResponse(code=0, msg=f"contact [{name}] 已存在, 更新成功!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            if create_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"contact [{name}] 创建失败! {create_response.json()}", data=create_response.json())
            else:
                return ReturnResponse(code=0, msg=f"contact [{name}] 创建成功!", data=create_response.json())
    
    def get_rack_id(self, name, tenant):
        api_url = '/api/dcim/racks/'
        parms = {
            "name": name,
            "tenant_id": self.get_tenant_id(name=tenant)
        }
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=parms)
        if response.json()['count'] > 1:
            raise ValueError(f"rack {name} 存在多个结果")
        elif response.json()['count'] == 0:
            return None
        else:
            return response.json()['results'][0]['id']
    
    def add_or_update_rack(self, 
                           site: str=None,
                           name: str=None,
                           status: Literal['active', 'reserved', 'deprecated']='active',
                           tenant: str=None,
                           u_height: int=None,
                           facility: str=None,
                        ):
        
        if status not in ['active', 'reserved', 'deprecated']:
            raise ValueError(f"rack status {status} 不合法!")
        
        api_url = '/api/dcim/racks/'
        data = {
            "site": self.get_site_id(name=site),
            "name": name,
            "status": status,
            "tenant": self.get_tenant_id(name=tenant),
            "u_height": u_height,
            "facility": facility
        }
        data = Parse.remove_dict_none_value(data)
        rack_id = self.get_rack_id(name=name, tenant=tenant)
        if rack_id:
            update_response = requests.put(url=self.url + api_url + f"{rack_id}/", headers=self.headers, json=data, timeout=self.timeout)
            if update_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"rack {name} 更新失败! {update_response.json()}", data=update_response.json())
            else:
                return ReturnResponse(code=0, msg=f"rack {name} 已存在, 更新成功!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            if create_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"rack {name} 创建失败! {create_response.json()}", data=create_response.json())
            else:
                return ReturnResponse(code=0, msg=f"rack {name} 创建成功!", data=create_response.json())
    
    def get_tags_id(self, name):
        api_url = '/api/extras/tags/'
        params = {
            "name": name
        }
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=params)
        if response.json()['count'] > 1:
            raise ValueError(f"tag {name} 存在多个结果")
        elif response.json()['count'] == 0:
            return None
        else:
            return response.json()['results'][0]['id']
    
    def add_or_update_tags(self, name: str, slug: str, color: str):
        api_url = '/api/extras/tags/'
        data = {
            "name": name,
            "slug": slug,
            "color": color,
        }
        tag_id = self.get_tags_id(name=name)
        if tag_id:
            update_response = requests.put(url=self.url + api_url + f"{tag_id}/", headers=self.headers, json=data, timeout=self.timeout)
            if update_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"tag {name} 更新失败! {update_response.json()}", data=update_response.json())
            else:
                return ReturnResponse(code=0, msg=f"tag {name} 已存在, 更新成功!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            if create_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"tag {name} 创建失败! {create_response.json()}", data=create_response.json())
            else:
                return ReturnResponse(code=0, msg=f"tag {name} 创建成功!", data=create_response.json())
    
    def get_interface_id(self, device, name):
        api_url = '/api/dcim/interfaces/'
        params = {
            "name": name,
            "device": device
        }
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=params)
        # print(response.json())
        if name is None or device is None:
            return None
        elif response.json()['count'] > 1:
            raise ValueError(f"interface {name} 存在多个结果")
        elif response.json()['count'] == 0:
            return None
        else:
            return response.json()['results'][0]['id']
    
    def add_or_update_interfaces(self, 
                                 name, 
                                 device, 
                                 interface_type: Literal['1000base-t', '2.5gbase-t', '1gfc-sfp', 'cisco-stackwise', 'other']='other',
                                 tenant: str=None,
                                 label: str=None,
                                 poe_mode: Literal['pd', 'pse']=None,
                                 poe_type: Literal['type2-ieee802.3at']=None,
                                 description: str=None):
        api_url = '/api/dcim/interfaces/'
        data = {
            "name": name,
            "device": self.get_device_id(name=device, tenant_id=self.get_tenant_id(name=tenant)),
            "type": interface_type,
            "label": label,
            # "status": status,
            # "type": type,
            # "mac_address": mac_address,
            # "lag": lag,
            "poe_mode": poe_mode,
            "poe_type": poe_type,
            "description": description,
        }
        data = Parse.remove_dict_none_value(data)
        interface_id = self.get_interface_id(name=name, device=device)
        if interface_id:
            update_response = requests.put(url=self.url + api_url + f"{interface_id}/", headers=self.headers, json=data, timeout=self.timeout)
            if update_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"interface {name} 更新失败! {update_response.json()}", data=update_response.json())
            else:   
                return ReturnResponse(code=0, msg=f"interface {name} 已存在, 更新成功!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            if create_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"interface {name} 创建失败! {create_response.json()}", data=create_response.json())
            else:
                return ReturnResponse(code=0, msg=f"interface {name} 创建成功!", data=create_response.json())
    
    def get_contact_role_id(self, name):
        api_url = '/api/tenancy/contact-roles/'
        params = {
            "name": name
        }
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=params)
        if response.json()['count'] > 1:
            raise ValueError(f"contact role {name} 存在多个结果")
        elif response.json()['count'] == 0:
            return None
        else:
            return response.json()['results'][0]['id']
    
    def add_or_update_contact_role(self, name: str):
        api_url = '/api/tenancy/contact-roles/'
        slug = self._process_slug(name=name)
        data = {
            "name": name,
            "slug": slug,
        }
        contact_role_id = self.get_contact_role_id(name=name)
        if contact_role_id:
            update_response = requests.put(url=self.url + api_url + f"{contact_role_id}/", headers=self.headers, json=data, timeout=self.timeout)
            if update_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"contact role {name} 更新失败! {update_response.json()}", data=update_response.json())
            else:   
                return ReturnResponse(code=0, msg=f"contact role {name} 已存在, 更新成功!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            if create_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"contact role {name} 创建失败! {create_response.json()}", data=create_response.json())
            else:
                return ReturnResponse(code=0, msg=f"contact role {name} 创建成功!", data=create_response.json())
    
    def is_contact_assignmentd(self, contact_id: int, object_type: Literal['dcim.site', 'dcim.location', 'dcim.rack', 'dcim.device', 'dcim.interface'], role: str):
        api_url = '/api/tenancy/contact-assignments/'
        params = {
            "contact_id": contact_id,
            "object_type": object_type,
            # "object_type_id": object_type_id,
            "role_id": role
        }
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=params)
        if response.json()['count'] > 0:
            return True
        
    def get_contact_assignment_id(self, contact_id: int, object_type: Literal['dcim.site', 'dcim.location', 'dcim.rack', 'dcim.device', 'dcim.interface'], role: str):
        api_url = '/api/tenancy/contact-assignments/'
        params = {
            "contact_id": contact_id,
            "object_type": object_type,
            "role_id": role
        }
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=params)
        return response.json()['results'][0]['id']
    
    def assign_contact_to_object(self, 
                                 contact: str, 
                                 object_type: Literal['dcim.site', 'dcim.location', 'dcim.rack', 'dcim.device', 'dcim.interface'], 
                                 object_name: str, 
                                 role: str,
                                 priority: Literal['primary', 'secondary', 'tertiary', 'inactive']='primary') -> ReturnResponse:
        api_url = '/api/tenancy/contact-assignments/'
        if object_type == 'dcim.site':
            object_id = self.get_site_id(name=object_name)
        elif object_type == 'dcim.location':
            object_id = self.get_location_id(name=object_name)
        elif object_type == 'dcim.rack':
            object_id = self.get_rack_id(name=object_name)
        elif object_type == 'dcim.device':
            object_id = self.get_device_id(name=object_name)
        elif object_type == 'dcim.interface':
            object_id = self.get_interface_id(name=object_name, device=object_name)
        else:
            raise ValueError(f"object type {object_type} 不存在")
        
        contact_id = self.get_contact_id(name=contact)
        
        data = {
            "contact": contact_id,
            "object_type": object_type,
            "object_id": object_id,
            "role": self.get_contact_role_id(name=role),
            "priority": priority,
        }
        is_contact_assignmentd = self.is_contact_assignmentd(contact_id=contact_id, object_type=object_type, role=self.get_contact_role_id(name=role))

        if is_contact_assignmentd:
            assign_id = self.get_contact_assignment_id(contact_id=contact_id, object_type=object_type, role=self.get_contact_role_id(name=role))
            data['id'] = assign_id
            update_response = requests.patch(url=self.url + api_url, headers=self.headers, data=json.dumps([data]), timeout=self.timeout)
            if update_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"contact {contact} 更新 {object_name} 的 {role} 失败! {update_response.json()}", data=update_response.json())
            else:
                return ReturnResponse(code=0, msg=f"contact {contact} 更新 {object_name} 成功!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            if create_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"contact {contact} 分配到 {object_name} 失败! {create_response.json()}", data=create_response.json())
            else:
                return ReturnResponse(code=0, msg=f"contact {contact} 分配到 {object_name} 成功!", data=create_response.json())
        
    
    def get_object_type(self):
        api_url = '/api/extras/object-types/'
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout)
        return response.json()['results']
    
    def get_object_type_id(self, name: Literal['dcim.site', 'dcim.location', 'dcim.rack', 'dcim.device', 'dcim.interface', 'dcim.device-type', 'dcim.manufacturer', 'dcim.virtual-chassis', 'dcim.cable', 'dcim.power-outlet', 'dcim.power-port', 'dcim.power-feed', 'dcim.power-panel', 'dcim.power-outlet-template', 'dcim.power-port-template', 'dcim.power-feed-template', 'dcim.power-panel-template']):
        api_url = '/api/extras/object-types/'
        app_label, model = name.split('.')[0], name.split('.')[1]
        params = {
            "app_label": app_label,
            "model": model
        }
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=params)
        if response.json()['count'] > 1:
            raise ValueError(f"object type {name} 存在多个结果")
        elif response.json()['count'] == 0:
            return None
        else:
            return response.json()['results'][0]['id']
    
    def get_site_id(self, name):
        api_url = '/api/dcim/sites/'
        params = {
            "name": name
        }
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=params)
        if name is None:
            return None
        elif response.json()['count'] > 1:
            raise ValueError(f"site {name} 存在多个结果")
        elif response.json()['count'] == 0:
            return None
        else:
            return response.json()['results'][0]['id']
    
    def add_or_update_sites(self, name, slug, tenant):
        # if status not in ['active', 'staging', 'planned', 'decommissioning', 'retired']:
        #     raise ValueError(f"site status {status} 不合法!")
        
        api_url = '/api/dcim/sites/'
        data = {
            "name": name,
            "slug": slug,
            "tenant": self.get_tenant_id(tenant)
        }
        data = Parse.remove_dict_none_value(data)
        site_id = self.get_site_id(name=name)
        if site_id:
            update_response = requests.put(url=self.url + api_url + f"{site_id}/", headers=self.headers, json=data, timeout=self.timeout)
            if update_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"site {name} 更新失败! {update_response.json()}", data=update_response.json())
            else:
                return ReturnResponse(code=0, msg=f"site {name} 已存在, 更新成功!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            if create_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"site {name} 创建失败! {create_response.json()}", data=create_response.json())
            else:
                return ReturnResponse(code=0, msg=f"site {name} 创建成功!", data=create_response.json())
    
    def get_devices(self, tenant: str=None, device_type: str=None, manufacturer: str=None):
        url = f"{self.url}/api/dcim/devices/"
        params = {
            "tenant": tenant,
            "device_type": device_type,
            "manufacturer_id": self.get_manufacturer_id(name=manufacturer),
            "limit": 0
        }
        params = Parse.remove_dict_none_value(params)
        results = []
        while url:
            r = requests.get(url=url, headers=self.headers, timeout=self.timeout, params=params)
            data = r.json()
            results.extend(data.get("results", []))

            url = data.get("next")   # next 自带 offset/limit
            params = None            # next 已经包含 query 了，别再重复传 params
        return results
    
    def get_power_port_id(self, device, name):
        api_url = '/api/dcim/power-ports/'
        params = {
            "name": name,
            "device": device
        }
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=params)
        if response.json()['count'] > 1:
            raise ValueError(f"power port {name} 存在多个结果")
        elif response.json()['count'] == 0:
            return None
        else:
            return response.json()['results'][0]['id']
    
    def add_or_update_power_ports(self, 
                                  device, 
                                  name, 
                                  power_type: Literal['iec-60320-c14', 'other'],
                                  label: str=None,
                                  maximum_draw: int=None,
                                  allocated_draw: int=None,
                                  mark_connected: bool=True,
                                  description: str=None,
                            ):
        '''
        添加/更新电源端口

        Args:
            device (str): 设备名称
            name (str): 电源端口名称
            power_type (Literal['iec-60320-c14', 'other']): 电源类型
            label (str, optional): 标签. Defaults to None.
            maximum_draw (int, optional): 设备满载最大功率
            allocated_draw (int, optional): 计划/分配”的功率, 如果不知道, 就和 maximum_draw 一样
            mark_connected (bool, optional): 是否标记为已连接. Defaults to True.
            description (str, optional): 描述. Defaults to None.
        '''
        api_url = '/api/dcim/power-ports/'
        data = {
            "device": self.get_device_id(name=device),
            "name": name,
            "type": power_type,
            "label": label,
            "maximum_draw": maximum_draw,
            "allocated_draw": allocated_draw,
            "mark_connected": mark_connected,
            "description": description,
        }
        data = Parse.remove_dict_none_value(data)
        power_port_id = self.get_power_port_id(name=name, device=device)
        if power_port_id:
            update_response = requests.put(url=self.url + api_url + f"{power_port_id}/", headers=self.headers, json=data, timeout=self.timeout)
            if update_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"power port [{device} {name}] updated failed! {update_response.json()}", data=update_response.json())
            else:
                return ReturnResponse(code=0, msg=f"power port [{device} {name}] exists, updated successfully!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            if create_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"power port [{device} {name}] created failed! {create_response.json()}", data=create_response.json())
            else:
                return ReturnResponse(code=0, msg=f"power port [{device} {name}] created successfully!", data=create_response.json())
    
    def get_console_port_id(self, device, name):
        api_url = '/api/dcim/console-ports/'
        params = {
            "name": name,
            "device": device
        }
        response = requests.get(url=self.url + api_url, headers=self.headers, timeout=self.timeout, params=params)
        if response.json()['count'] > 1:
            raise ValueError(f"console port {name} 存在多个结果")
        elif response.json()['count'] == 0:
            return None
        else:
            return response.json()['results'][0]['id']
    
    def add_or_update_console_port(self, device, name, port_type: Literal['rj-45']='rj-45', description: str=None):
        api_url = '/api/dcim/console-ports/'
        data = {
            "device": self.get_device_id(name=device),
            "name": name,
            "type": port_type,
            "description": description,
        }
        data = Parse.remove_dict_none_value(data)
        console_port_id = self.get_console_port_id(name=name, device=device)
        if console_port_id:
            update_response = requests.put(url=self.url + api_url + f"{console_port_id}/", headers=self.headers, json=data, timeout=self.timeout)
            if update_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"console port [{device} {name}] updated failed! {update_response.json()}", data=update_response.json())
            else:
                return ReturnResponse(code=0, msg=f"console port [{device} {name}] exists, updated successfully!", data=update_response.json())
        else:
            create_response = requests.post(url=self.url + api_url, headers=self.headers, json=data, timeout=self.timeout)
            if create_response.status_code > 210:
                return ReturnResponse(code=1, msg=f"console port [{device} {name}] created failed! {create_response.json()}", data=create_response.json())
            else:
                return ReturnResponse(code=0, msg=f"console port [{device} {name}] created successfully!", data=create_response.json())