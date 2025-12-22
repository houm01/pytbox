#!/usr/bin/env python3

from typing import Any, List, Literal
import requests
import time
from datetime import datetime, timezone, timedelta
from ..utils.response import ReturnResponse


class Meraki:
    '''
    Meraki Client
    '''    
    def __init__(self,
                 api_key: str=None,
                 organization_id: str=None,
                 timeout: int=10,
                 region: Literal['global', 'china']='china',
                 retry_max_retries: int=5,
                 retry_backoff_factor: float=1.0,
                 retry_on_status: tuple[int, ...]=(429, 500, 502, 503, 504)):
        '''
        Meraki API 客户端
        
        Args:
            api_key: Meraki API Key
            organization_id: 组织 ID
            timeout: 单次 HTTP 请求超时时间（秒）
            region: 接口区域，'china' 或 'global'
            retry_max_retries:
                - 最大尝试次数（包含首次请求）。例如设为 5，表示“首发 + 最多重试 4 次”。
                - 用于在遇到限流(429)或临时性错误(5xx/网络波动/超时)时的上限保护，避免无限重试。
            retry_backoff_factor:
                - 指数退避的基数，实际等待时间为 backoff_factor × (2 ** attempt) 秒，attempt 从 0 开始。
                - 例：factor=1.0 -> 等待序列 1s、2s、4s、8s、16s……
                - 若响应为 429 且带有 Retry-After 头，将优先使用该头的秒数；没有该头时才使用指数退避。
                - 建议：常规读取/监控 1.0～1.5；批量变更 1.5～2.0（更温和，降低撞限概率）。
            retry_on_status:
                - 会触发重试的 HTTP 状态码集合。默认值为 (429, 500, 502, 503, 504)：
                  - 429：命中 Meraki 限流，需等待后重试（优先使用 Retry-After）。
                  - 5xx：一般为临时性错误，按指数退避重试。
        
        Notes:
            - 429（API 限流）时，优先读取响应头 Retry-After 等待指定秒数；若无该头，则按指数退避计算等待。
            - 该客户端还会对网络异常（如超时、连接错误）进行指数退避重试，次数受 retry_max_retries 限制。
            - Meraki 官方限流与配额说明参见：
              https://developer.cisco.com/meraki/api-v1/rate-limit/
              概要：每组织稳态 10 req/s，2 秒内最多约 30 次突发；每源 IP 100 req/s。
        '''
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
        # 请求重试相关默认配置
        self.retry_max_retries = retry_max_retries
        self.retry_backoff_factor = retry_backoff_factor
        self.retry_on_status = retry_on_status

    def _request(self,
                 method: Literal['GET', 'POST', 'PUT', 'DELETE'],
                 url: str,
                 max_retries: int | None = None,
                 backoff_factor: float | None = None,
                 retry_on: tuple[int, ...] | None = None,
                 **kwargs) -> ReturnResponse:
        """
        通用请求方法，处理 Meraki API 限流与暂时性错误的重试。
        - 429: 优先使用 Retry-After 头；缺失则按指数退避
        - 5xx/网络错误: 指数退避
        """
        # 使用实例级默认配置，支持调用时临时覆盖
        if max_retries is None:
            max_retries = self.retry_max_retries
        if backoff_factor is None:
            backoff_factor = self.retry_backoff_factor
        if retry_on is None:
            retry_on = self.retry_on_status
        last_exc: Exception | None = None
        resp: requests.Response | None = None
        for attempt in range(max_retries):
            try:
                resp = requests.request(method, url, **kwargs)
                if resp.status_code in retry_on:
                    if resp.status_code == 429:
                        retry_after = resp.headers.get("Retry-After")
                        if retry_after:
                            try:
                                sleep_s = float(retry_after)
                            except ValueError:
                                sleep_s = backoff_factor * (2 ** attempt)
                        else:
                            sleep_s = backoff_factor * (2 ** attempt)
                    else:
                        sleep_s = backoff_factor * (2 ** attempt)
                    time.sleep(sleep_s)
                    continue
                if 200 <= resp.status_code < 300:
                    try:
                        data = resp.json()
                    except ValueError:
                        data = resp.text
                    return ReturnResponse(code=0, msg="OK", data=data)
                return ReturnResponse(code=1, msg=f"{resp.status_code} - {resp.text}", data=None)
            except (requests.Timeout, requests.ReadTimeout, requests.ConnectionError) as e:
                last_exc = e
                time.sleep(backoff_factor * (2 ** attempt))
                continue
        if resp is not None:
            try:
                data = resp.json()
            except Exception:
                data = None
            return ReturnResponse(code=1, msg=f"{resp.status_code} - {resp.text}", data=data)
        if last_exc:
            return ReturnResponse(code=1, msg=str(last_exc), data=None)
        return ReturnResponse(code=1, msg="Request failed after retries", data=None)

    def get_organizations(self) -> ReturnResponse:
        '''
        https://developer.cisco.com/meraki/api-v1/get-organizations/
        '''
        r = self._request(
            "GET",
            f"{self.base_url}/organizations",
            headers=self.headers,
            timeout=self.timeout
        )
        if r.code == 0:
            return ReturnResponse(code=0, msg=f"获取组织成功", data=r.data)
        return ReturnResponse(code=1, msg=f"获取组织失败: {r.msg}")

    def get_api_requests(self, timespan: int=5*60) -> ReturnResponse:
        
        params = {}
        params['timespan'] = timespan
        
        r = self._request(
            "GET",
            url=f"{self.base_url}/organizations/{self.organization_id}/apiRequests",
            headers=self.headers,
            params=params,
            timeout=self.timeout
        )
        if r.code == 0:
            return ReturnResponse(code=0, msg='获取 API 请求数量成功', data=r.data)
        return ReturnResponse(code=1, msg=f"获取 API 请求失败: {r.msg}", data=None)

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
        
        params['perPage'] = 1000
        
        r = self._request(
            "GET",
            f"{self.base_url}/organizations/{self.organization_id}/networks",
            headers=self.headers,
            params=params,
            timeout=self.timeout
        )
        if r.code == 0:
            data = r.data
            size = len(data) if isinstance(data, list) else 0
            return ReturnResponse(code=0, msg=f"获取到 {size} 个网络", data=data)
        return ReturnResponse(code=1, msg=f"获取网络失败: {r.msg}")

    def get_network(self, network_id: str) -> ReturnResponse:
        '''
        https://developer.cisco.com/meraki/api-v1/get-network/

        Args:
            network_id (str): _description_

        Returns:
            ReturnResponse: _description_
        '''
        r = self._request(
            method='GET',
            url=f"{self.base_url}/networks/{network_id}",
            headers=self.headers,
            timeout=self.timeout,
        )
        return r
    
    def create_network(self, 
                       name=None, 
                       product_types: list=['switch', 'wireless'], 
                       config_template_id=None, 
                       tags=[], 
                       notes=None,
                       is_bound_to_config_template: bool=True
                    ):
        '''
        https://developer.cisco.com/meraki/api-v1/create-organization-network/
        '''
        # /organizations/{organizationId}/networks
        payload = {
                "productTypes": product_types,
                "configTemplateId": config_template_id,
                "name": name,
                "timeZone": "Asia/Shanghai",
                # "enrollmentString": null,
                "tags": tags,
                "notes": notes,
                "isBoundToConfigTemplate": is_bound_to_config_template,
                "isVirtual": False,
                "details": None
        }
        r = self._request(
            method='POST',
            url=f"{self.base_url}/organizations/{self.organization_id}/networks",
            headers=self.headers,
            timeout=self.timeout,
            json=payload
        )
        return r
    
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

    def get_switch_stacks(self, network_id: str=None) -> ReturnResponse:
        '''
        https://developer.cisco.com/meraki/api-v1/get-network-switch-stacks/
        '''
        r = requests.get(
            url=f"{self.base_url}/networks/{network_id}/switch/stacks",
            headers=self.headers,
            timeout=self.timeout
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f"获取堆叠成功", data=r.json())
        return ReturnResponse(code=1, msg=f"获取堆叠失败", data=r.text)

    def create_switch_stack(self, network_id: str=None, stack_name:str='new stack', serials:list =[]) -> ReturnResponse:
        '''
        _summary_

        Args:
            network_id (str, optional): _description_. Defaults to None.
            stack_name (str, optional): _description_. Defaults to 'new stack'.
            serials (list, optional): _description_. Defaults to [].

        Returns:
            ReturnResponse: _description_
        '''
        body = {
            "name": stack_name,
            "serials": serials,
        }

        response = requests.post(
            url=f"{self.base_url}/networks/{network_id}/switch/stacks",
            headers=self.headers,
            timeout=self.timeout,
            json=body
        )
        if response.status_code == 200:
            return ReturnResponse(code=0, msg=f"network_id: {network_id}, stack_name: {stack_name}, serials: {serials} 创建成功", data=response.json())
        else:
            return ReturnResponse(code=1, msg=f"network_id: {network_id}, stack_name: {stack_name}, serials: {serials} 创建失败: {response.status_code} - {response.json()}", data=None)


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
            
        r = self._request(
            "GET",
            f"{self.base_url}/organizations/{self.organization_id}/inventory/devices", 
            headers=self.headers,
            params=params,
            timeout=self.timeout
        )
        if r.code == 0:
            data = r.data
            size = len(data) if isinstance(data, list) else 0
            return ReturnResponse(code=0, msg=f"获取到 {size} 个设备", data=data)
        return ReturnResponse(code=1, msg=f"获取设备失败: {r.msg}")

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
        r = self._request(
            "GET",
            f"{self.base_url}/devices/{serial}",
            headers=self.headers,
            timeout=self.timeout
        )
        if r.code == 0:
            return ReturnResponse(code=0, msg=f"获取设备详情成功", data=r.data)
        # 兼容历史约定：404 映射为 code=3
        if isinstance(r.msg, str) and r.msg.startswith("404"):
            return ReturnResponse(code=3, msg=f"设备 {serial} 还未添加过", data=None)
        return ReturnResponse(code=1, msg=f"获取设备详情失败: {r.msg}", data=None)

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
    
    def timestamp_to_iso8601(self, timestamp: int) -> str:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    def get_network_events(self, 
                           network_id, 
                           product_type: Literal['wireless', 'switch']=None, 
                           serial: str=None, 
                           device_name: str=None,
                           last_minute: int=5,
                           perpage: int=100,
                           included_event_types: list=None
                        ) -> ReturnResponse:
        '''
        拉取最近 N 分钟内的网络事件，自动按 Link 头翻页（参考 111.py 实现）。

        Args:
            network_id: 网络 ID
            product_type: 设备类型过滤（无线/交换：'wireless'/'switch'），多产品网络建议必填
            serial: 设备序列号过滤
            device_name: 设备名称过滤
            last_minute: 最近 N 分钟（默认 5）
            perpage: 每页返回条数（3-1000，默认 100）
            included_event_types: 事件类型字符串列表（需与接口返回的 eventTypes 完全匹配）
                - 注意：必须传"事件类型标识"的精确字符串，而不是人类可读描述
                - 建议先调用 get_event_types(network_id) 获取可用类型，再选择其子集传入
                - 传参编码方式为 includedEventTypes[]（本方法已代为处理）
                - 常用认证/802.1X/Radius 相关示例（不同网络可用集合可能不同，以 get_event_types 返回为准）：
                    [
                        "8021x_auth",
                        "8021x_eap_success",
                        "8021x_eap_failure",
                        "8021x_radius_timeout",
                        "8021x_client_timeout",
                        "8021x_guest_auth",
                        "8021x_critical_auth",
                        "8021x_deauth",
                        "8021x_client_deauth",
                        "radius_mac_auth",
                        "radius_mab_timeout",
                        "radius_dynamic_vlan_assignment",
                        "radius_invalid_group_policy",
                        "radius_invalid_vlan_name",
                        "radius_proxy_tls_success",
                        "radius_proxy_tls_fail"
                    ]

        Returns:
            ReturnResponse: data 结构与 Meraki API 一致，包含 message/pageStartAt/pageEndAt/events
        '''
        # 计算时间窗口（UTC）
        t1_dt = datetime.now(tz=timezone.utc)
        t0_dt = t1_dt - timedelta(minutes=last_minute)
        
        # 基于 endingBefore 的手动翻页：
        # - 首次请求使用 t0/t1（限定窗口）
        # - 随后使用 endingBefore=上一页最旧事件时间，持续向更旧时间翻页，直到越过 t0 或无更多事件
        base_params: dict[str, Any] = {
            'perPage': max(3, min(int(perpage), 1000))
        }
        if product_type:
            base_params['productType'] = product_type
        if serial:
            base_params['deviceSerial'] = serial
        if device_name:
            base_params['deviceName'] = device_name
        if isinstance(included_event_types, list) and included_event_types:
            base_params['includedEventTypes[]'] = included_event_types

        all_events: list[dict] = []
        url = f"{self.base_url}/networks/{network_id}/events"
        page = 0
        current_ending_before: datetime | None = None

        while True:
            page += 1
            # 组装本次请求参数
            params: dict[str, Any] = dict(base_params)
            if page == 1:
                params['t0'] = t0_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                params['t1'] = t1_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                # 第二页及后续：改用 endingBefore，且不再传 t1，避免与分页游标冲突
                if current_ending_before is None:
                    break
                params['t0'] = t0_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                params['endingBefore'] = current_ending_before.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            # 带重试的请求
            attempt = 0
            max_retries = self.retry_max_retries
            while True:
                attempt += 1
                try:
                    resp = requests.get(url, headers=self.headers, params=params, timeout=self.timeout)
                    status = resp.status_code
                    if status == 429 or 500 <= status < 600:
                        if attempt > max_retries:
                            return ReturnResponse(code=1, msg=f"获取网络事件失败（多次重试后仍为 {status}）", data=None)
                        retry_after = resp.headers.get("Retry-After") or resp.headers.get("retry-after")
                        if retry_after:
                            try:
                                delay = float(retry_after)
                            except ValueError:
                                delay = 1.0 * attempt
                        else:
                            delay = 1.0 * attempt
                        time.sleep(delay)
                        continue
                    resp.raise_for_status()
                    break
                except (requests.Timeout, requests.ReadTimeout, requests.ConnectionError) as e:
                    if attempt > max_retries:
                        return ReturnResponse(code=1, msg=f"获取网络事件失败: {str(e)}", data=None)
                    time.sleep(1.0 * attempt)
                    continue

            body = resp.json()
            page_events = body.get("events", [])
            if not isinstance(page_events, list):
                page_events = []

            # 本地时间过滤
            filtered_events = []
            oldest_dt_on_page: datetime | None = None
            for ev in page_events:
                occurred_at_str = ev.get("occurredAt")
                if not occurred_at_str:
                    continue
                try:
                    occurred_dt = datetime.fromisoformat(occurred_at_str.replace("Z", "+00:00"))
                except Exception:
                    continue
                if oldest_dt_on_page is None or occurred_dt < oldest_dt_on_page:
                    oldest_dt_on_page = occurred_dt
                if t0_dt <= occurred_dt <= t1_dt:
                    filtered_events.append(ev)

            all_events.extend(filtered_events)

            # 结束条件：无数据或已越过窗口下界
            if not page_events:
                break
            if oldest_dt_on_page is None or oldest_dt_on_page <= t0_dt:
                break

            # 推进游标：下一轮以本页最旧事件时间作为 endingBefore
            # 减去 1 微秒以避免边界重复
            current_ending_before = oldest_dt_on_page - timedelta(microseconds=1)

        # 规范化返回结构
        t0_str = t0_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        t1_str = t1_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        if all_events:
            occurred_list = []
            for ev in all_events:
                if ev.get("occurredAt"):
                    try:
                        occurred_list.append(datetime.fromisoformat(ev["occurredAt"].replace("Z", "+00:00")))
                    except Exception:
                        pass
            if occurred_list:
                page_start_at = min(occurred_list).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                page_end_at = max(occurred_list).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                page_start_at = t0_str
                page_end_at = t1_str
        else:
            page_start_at = t0_str
            page_end_at = t1_str

        result = {
            "message": None if all_events else "no events in the time window",
            "pageStartAt": page_start_at,
            "pageEndAt": page_end_at,
            "events": all_events
        }
        return ReturnResponse(code=0, msg=f"获取到 {len(all_events)} 个网络事件", data=result)
    
    def get_event_types(self, network_id):
        '''
        获取指定网络支持的事件类型枚举，用于辅助构造 includedEventTypes 过滤条件。

        Args:
            network_id (str): 网络 ID（必填）

        Returns:
            ReturnResponse:
                - code = 0: 成功，data 为接口返回的 JSON（通常是事件类型数组）
                - code = 1: 失败，msg 包含错误信息

        使用示例:
            r = client.get_event_types(network_id='L_xxx')
            if r.code == 0:
                # r.data 通常为形如 [{'type': 'association'}, {'type': 'auth_fail'}, ...]
                types = [i.get('type') for i in r.data if isinstance(i, dict)]
                # 然后在 get_network_events 中作为 included_event_types 传入精确字符串
                client.get_network_events(
                    network_id='L_xxx',
                    product_type='wireless',
                    included_event_types=['auth_fail'],  # 示例
                    last_minute=5
                )
        '''
        # 支持翻页：完全参考 111.py，直接使用 requests
        all_types: list = []
        url = f"{self.base_url}/networks/{network_id}/events/eventTypes"
        
        while True:
            attempt = 0
            max_retries = self.retry_max_retries
            
            while True:
                attempt += 1
                try:
                    resp = requests.get(url, headers=self.headers, timeout=self.timeout)
                    
                    status = resp.status_code
                    if status == 429 or 500 <= status < 600:
                        if attempt > max_retries:
                            return ReturnResponse(code=1, msg=f"获取事件类型失败（多次重试后仍为 {status}）", data=None)
                        
                        retry_after = resp.headers.get("Retry-After") or resp.headers.get("retry-after")
                        if retry_after:
                            try:
                                delay = float(retry_after)
                            except ValueError:
                                delay = 1.0 * attempt
                        else:
                            delay = 1.0 * attempt
                        time.sleep(delay)
                        continue
                    
                    resp.raise_for_status()
                    break
                except (requests.Timeout, requests.ReadTimeout, requests.ConnectionError) as e:
                    if attempt > max_retries:
                        return ReturnResponse(code=1, msg=f"获取事件类型失败: {str(e)}", data=None)
                    time.sleep(1.0 * attempt)
                    continue
            
            payload = resp.json()
            
            # 累加当前页
            if isinstance(payload, list):
                all_types.extend(payload)
            elif isinstance(payload, dict) and 'types' in payload and isinstance(payload['types'], list):
                all_types.extend(payload['types'])
            
            # 使用 requests 的 .links 属性获取下一页（与 111.py 完全一致）
            if "next" in resp.links:
                url = resp.links["next"]["url"]
            else:
                break
        
        return ReturnResponse(code=0, msg=f"获取到 {len(all_types)} 种事件类型", data=all_types)
 
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
        
        if isinstance(serials, str):
            serials = [serials]
        
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
        
        # print(r.text)
        if len(already_claimed_serials) == len(serials):
            code = 0
            msg = f"All {len(already_claimed_serials)} devices are already claimed"
        elif len(already_claimed_serials) > 0:
            code = 0
            msg = f"Some {len(already_claimed_serials)} devices are already claimed"
        else:
            code = 1
            msg = f"Claim network devices failed"
        
        return ReturnResponse(code=code, msg=msg)

    # def update_device(self, serial: str, name: str=None, tags: list=None, address: str=None, lat: float=None, lng: float=None) -> ReturnResponse:
    #     '''
    #     https://developer.cisco.com/meraki/api-v1/update-device/
    #     '''
    #     body = {}
    #     if name:
    #         body['name'] = name
    #     if tags:
    #         body['tags'] = tags
    #     if address:
    #         body['address'] = address
    #     if lat:
    #         body['lat'] = lat
    #     if lng:
    #         body['lng'] = lng
            
    #     r = requests.put(
    #         url=f"{self.base_url}/devices/{serial}",
    #         headers=self.headers,
    #         json=body,
    #         timeout=self.timeout
    #     )

    def get_switch_profiles(self, config_template_id: str=None) -> ReturnResponse:
        response = requests.get(
            url=f"{self.base_url}/organizations/{self.organization_id}/configTemplates/{config_template_id}/switch/profiles",
            headers=self.headers,
            timeout=self.timeout
        )
        if response.status_code == 200:
            return ReturnResponse(code=0, msg='', data=response.json())
        else:
            return ReturnResponse(code=1, msg='获取失败',data=response.text)
    
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
            device_detail = self.get_device_detail(serial=serial).data
            if device_detail:
                model = device_detail.get('model')
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
            timeout=self.timeout
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
            url=f"{self.base_url}/devices/{serial}/switch/ports",
            headers=self.headers,
            timeout=self.timeout
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f"获取交换机端口状态成功", data=r.json())
        return ReturnResponse(code=1, msg=f"获取交换机端口状态失败: {r.status_code} - {r.text}", data=None)
    
    

    def get_switch_port(self, serial, port_id):
        '''
        https://developer.cisco.com/meraki/api-v1/get-device-switch-port/
        '''
        r = self._request(
            method='GET',
            url=f"{self.base_url}/devices/{serial}/switch/ports/{port_id}",
            headers=self.headers,
            timeout=self.timeout,
        )
        if r.code == 0:
            return ReturnResponse(code=0, msg=f"获取交换机端口成功", data=r.data)
        return ReturnResponse(code=1, msg=f"获取交换机端口失败: {r.status_code} - {r.text}", data=None)
    
    def update_switch_port(self, serial, port_id, body) -> ReturnResponse:
        '''
        update switch port
        https://developer.cisco.com/meraki/api-v1/update-device-switch-port/

        Args:
            serial (str): 设备序列号
            port_id (str): 端口ID
            body (dict): 更新内容

        Returns:
            ReturnResponse:
                - code = 0: 成功，data 为接口返回的 JSON
                - code = 1: 失败，msg 包含错误信息
        '''
        r = self._request(
            method='PUT',
            url=f"{self.base_url}/devices/{serial}/switch/ports/{port_id}",
            headers=self.headers,
            timeout=self.timeout,
            json=body
        )
        if r.code == 0:
            return ReturnResponse(code=0, msg=f"更新交换机端口 {port_id} 成功", data=body)
        return ReturnResponse(code=1, msg=f"更新交换机端口 {port_id} 失败", data=body)
    
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
            return ReturnResponse(code=0, msg=f"获取 SSID 成功", data=r.json())
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
    
    def get_ssid_by_name(self, network_id, ssid_name):
        '''
        https://developer.cisco.com/meraki/api-v1/get-network-wireless-ssid-by-name/
        '''
        r = self.get_ssids(network_id=network_id)
        if r.code == 0:
            for ssid in r.data:
                if ssid['name'] == ssid_name:
                    return ssid
        return None

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
    
    def is_ssid_exists(self, network_id, ssid_name) -> bool:
        '''
        Args:
            network_id (str): 网络ID
            ssid_name (str): SSID名称

        Returns:
            bool: True 表示存在, False 表示不存在
        '''
        r = self.get_ssids(network_id=network_id)
        if r.code == 0:
            for ssid in r.data:
                if ssid['name'] == ssid_name:
                    return True
        return False
        
    def create_ssid(self, network_id, ssid_name) -> ReturnResponse:
        if self.is_ssid_exists(network_id=network_id, ssid_name=ssid_name):
            return ReturnResponse(code=0, msg=f"SSID {ssid_name} 已存在", data=None)
        
        body = {
            "name": ssid_name,
            "enabled": True
        }
        r = requests.post(
            url=f"{self.base_url}/networks/{network_id}/wireless/ssids",
            headers=self.headers,
            timeout=self.timeout,
            json=body
        )
    
    def get_network_syslog_servers(self, network_id: str) -> ReturnResponse:
        '''
        https://developer.cisco.com/meraki/api-v1/get-network-syslog-servers/

        Args:
            network_id (str): _description_

        Returns:
            ReturnResponse: _description_
        '''
        r = requests.get(
            url=f"{self.base_url}/networks/{network_id}/syslogServers",
            headers=self.headers,
            timeout=self.timeout
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f"获取网络 syslog 服务器成功", data=r.json())
        return ReturnResponse(code=1, msg=f"获取网络 syslog 服务器失败: {r.status_code} - {r.text}", data=None)
    
    def update_network_syslog_servers(self, network_id: str, payload: dict) -> ReturnResponse:
        '''
        https://developer.cisco.com/meraki/api-v1/update-network-syslog-servers/

        Args:
            network_id (str): _description_
            payload (dict): _description_

        Returns:
            ReturnResponse: _description_
        '''
        r = requests.put(
            url=f"{self.base_url}/networks/{network_id}/syslogServers",
            headers=self.headers,
            timeout=self.timeout,
            json=payload
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f"更新网络 syslog 服务器成功", data=r.json())
        return ReturnResponse(code=1, msg=f"更新网络 syslog 服务器失败: {r.status_code} - {r.text}", data=None)
    
    def get_org_config_templates(self) -> ReturnResponse:
        '''
        https://developer.cisco.com/meraki/api-v1/get-organization-config-templates/
        '''
        r = requests.get(
            url=f"{self.base_url}/organizations/{self.organization_id}/configTemplates",
            headers=self.headers,
            timeout=self.timeout
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f"获取组织配置模板成功", data=r.json())
        return ReturnResponse(code=1, msg=f"获取组织配置模板失败: {r.status_code} - {r.text}", data=None)

    def remove_network_device(self, network_id: str, serial: str) -> ReturnResponse:
        '''
        https://developer.cisco.com/meraki/api-v1/remove-network-device/
        '''
        r = requests.post(
            url=f"{self.base_url}/networks/{network_id}/devices/remove",
            headers=self.headers,
            json={"serial": serial},
            timeout=self.timeout
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f"移除设备 {serial} 成功", data=None)
        else:
            if 'Device does not belong to a network' in r.text:
                return ReturnResponse(code=0, msg="设备不存在于网络中", data=None)
        return ReturnResponse(code=1, msg=f"移除设备 {serial} 失败: {r.status_code} - {r.text}", data=None)

    def delete_switch_stack(self, network_id: str, stack_id: str) -> ReturnResponse:
        '''
        https://developer.cisco.com/meraki/api-v1/delete-network-switch-stack/
        '''
        r = requests.delete(
            url=f"{self.base_url}/networks/{network_id}/switch/stacks/{stack_id}",
            headers=self.headers,
            timeout=self.timeout
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f"删除堆叠 {stack_id} 成功", data=None)
        return ReturnResponse(code=1, msg=f"删除堆叠 {stack_id} 失败: {r.status_code} - {r.text}", data=r.text)

    def bind_network_template(self, network_id: str, config_template_id: str, auto_bind: bool=False) -> ReturnResponse:
        '''
        hhttps://developer.cisco.com/meraki/api-v1/bind-network/
        '''
        body = {
            "configTemplateId": config_template_id,
            "autoBind": auto_bind
        }
        r = requests.post(
            url=f"{self.base_url}/networks/{network_id}/bind",
            headers=self.headers,
            json={"configTemplateId": config_template_id, "autoBind": auto_bind},
            timeout=self.timeout
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f"绑定模板 {config_template_id} 成功", data=None)
        return ReturnResponse(code=1, msg=f"绑定模板 {config_template_id} 失败: {r.status_code} - {r.text}", data=r.text)
   
    def update_network(self, network_id: str, tags: List[str]=None) -> ReturnResponse:
        '''
        https://developer.cisco.com/meraki/api-v1/update-network/
        
        Args:
            network_id (str): 网络ID
            tags (List[str]): 标签列表

        Returns:
            ReturnResponse: 返回更新结果
        '''
        payload = {}
        if tags:
            payload['tags'] = tags
            
        r = requests.put(
            url=f"{self.base_url}/networks/{network_id}",
            headers=self.headers,
            json=payload,
            timeout=self.timeout
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f"更新网络 {network_id} 成功", data=r.json())
        return ReturnResponse(code=1, msg=f"更新网络 {network_id} 失败: {r.status_code} - {r.text}", data=r.text)