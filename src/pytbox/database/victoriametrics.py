#!/usr/bin/env python3

import time
import json
from typing import Literal, Optional, Dict, List
import requests
from ..utils.response import ReturnResponse
from ..utils.load_vm_devfile import load_dev_file


class VictoriaMetrics:
    
    def __init__(self, url: str='', timeout: int=3, env: str='prod') -> None:
        self.url = url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.env = env

    def insert(self, metric_name: str = '', labels: Dict[str, str] = None, 
               value: List[float] = None, timestamp: int = None) -> ReturnResponse:
        """插入指标数据。
        
        Args:
            metric_name: 指标名称
            labels: 标签字典
            value: 值列表
            timestamp: 时间戳（毫秒），默认为当前时间
            
        Raises:
            requests.RequestException: 当请求失败时抛出
        """
        if labels is None:
            labels = {}
        if value is None:
            value = 1
        if timestamp is None:
            timestamp = int(time.time() * 1000)
            
        url = f"{self.url}/api/v1/import"
        data = {
            "metric": {
                "__name__": metric_name,
                **labels
            },
            "values": [value],
            "timestamps": [timestamp]
        }
        
        try:
            response = requests.post(url, json=data, timeout=self.timeout)
            return ReturnResponse(code=0, msg=f"数据插入成功，状态码: {response.status_code}, metric_name: {metric_name}, labels: {labels}, value: {value}, timestamp: {timestamp}")
        except requests.RequestException as e:
            return ReturnResponse(code=1, msg=f"数据插入失败: {e}")

    def query(self, query: str=None, output_format: Literal['json']=None) -> ReturnResponse:
        '''
        查询指标数据

        Args:
            query (str): 查询语句

        Returns:
            dict: 查询结果
        '''
        url = f"{self.url}/prometheus/api/v1/query"
        r = requests.get(
            url, 
            timeout=self.timeout,
            params={"query": query}
        )
        res_json = r.json()
        status = res_json.get("status")
        result = res_json.get("data", {}).get("result", [])
        is_json = output_format == 'json'

        if status == "success":
            if result:
                code = 0
                msg = f"[{query}] 查询成功!"
                data = result
            else:
                code = 2
                msg = f"[{query}] 没有查询到结果"
                data = res_json
        else:
            code = 1
            msg = f"[{query}] 查询失败: {res_json.get('error')}"
            data = res_json

        resp = ReturnResponse(code=code, msg=msg, data=data)

        if is_json:
            json_result = json.dumps(resp.__dict__, ensure_ascii=False)
            return json_result
        else:
            return resp

    def query_range(self, query):
        '''
        查询指标数据

        Args:
            query (str): 查询语句

        Returns:
            dict: 查询结果
        '''
        url = f"{self.url}/prometheus/api/v1/query_range"

        data = {
            'query': query,
            'start': '-1d',
            'step': '1h'
        }

        r = requests.post(url, data=data, timeout=self.timeout)
        res_json = r.json()
        print(res_json)
        # status = res_json.get("status")
        # result = res_json.get("data", {}).get("result", [])
        # is_json = output_format == 'json'

        # if status == "success":
        #     if result:
        #         code = 0
        #         msg = f"[{query}] 查询成功!"
        #         data = result
        #     else:
        #         code = 2
        #         msg = f"[{query}] 没有查询到结果"
        #         data = res_json
        # else:
        #     code = 1
        #     msg = f"[{query}] 查询失败: {res_json.get('error')}"
        #     data = res_json

        # resp = ReturnResponse(code=code, msg=msg, data=data)

        # if is_json:
        #     json_result = json.dumps(resp.__dict__, ensure_ascii=False)
        #     return json_result
        # else:
        #     return resp
    def get_labels(self, metric_name: str) -> ReturnResponse:
        url = f"{self.url}/api/v1/series?match[]={metric_name}"
        response = requests.get(url, timeout=self.timeout)
        results = response.json()
        if results['status'] == 'success':
            return ReturnResponse(code=0, msg=f"metric name: {metric_name} 获取到 {len(results['data'])} 条数据", data=results['data'])
        else:
            return ReturnResponse(code=1, msg=f"metric name: {metric_name} 查询失败")

    def check_ping_result(self, target: str, last_minute: int=10, env: str='prod', dev_file: str='') -> ReturnResponse:
        '''
        检查ping结果

        Args:
            target (str): 目标地址
            last_minute (int, optional): 最近多少分钟. Defaults to 10.
            env (str, optional): 环境. Defaults to 'prod'.
            dev_file (str, optional): 开发文件. Defaults to ''.

        Returns:
            ReturnResponse: 
                code = 0 正常, code = 1 异常, code = 2 没有查询到数据, 建议将其判断为正常
        '''
        query = f'min_over_time(ping_result_code{{target="{target}"}}[{last_minute}m])'
        # query = f'avg_over_time((ping_result_code{{target="{target}"}})[{last_minute}m])'
        if self.env == 'dev':
            r = load_dev_file(dev_file)
        else:
            r = self.query(query=query)
        if r.code == 0:
            value = r.data[0]['value'][1]
            if value == '0':
                return ReturnResponse(code=0, msg=f"已检查 {target} 最近 {last_minute} 分钟是正常的!", data=r.data)
            else:
                return ReturnResponse(code=1, msg=f"已检查 {target} 最近 {last_minute} 分钟是异常的!", data=r.data)
        else:
            return r

    def check_unreachable_ping_result(self, dev_file: str='') -> ReturnResponse:
        '''
        检查ping结果

        Args:
            target (str): 目标地址
            last_minute (int, optional): 最近多少分钟. Defaults to 10.
            env (str, optional): 环境. Defaults to 'prod'.
            dev_file (str, optional): 开发文件. Defaults to ''.

        Returns:
            ReturnResponse: 
                code = 0 正常, code = 1 异常, code = 2 没有查询到数据, 建议将其判断为正常
        '''
        query = "ping_result_code == 1"
        
        if self.env == 'dev':
            r = load_dev_file(dev_file)
        else:
            r = self.query(query=query)
        return r

    def check_interface_rate(self,
                             direction: Literal['in', 'out'],
                             sysName: str, 
                             ifName:str, 
                             last_minutes: Optional[int] = None
                            ) -> ReturnResponse:
        """查询指定设备的入方向总流量速率（bps）。

        使用 PromQL 对 `snmp_interface_ifHCInOctets` 进行速率计算并聚合到设备级别，
        将结果从字节每秒转换为比特每秒（乘以 8）。

        Args:
            sysName: 设备 `sysName` 标签值。
            last_minutes: 计算速率的时间窗口（分钟）。未提供时默认使用 5 分钟窗口。

        Returns:
            ReturnResponse: 查询结果包装。
        """
        if direction == 'in':
            query = f'(rate(snmp_interface_ifHCInOctets{{sysName="{sysName}", ifName="{ifName}"}}[{last_minutes}m])) * 8 / 1000000'
        else:
            query = f'(rate(snmp_interface_ifHCOutOctets{{sysName="{sysName}", ifName="{ifName}"}}[{last_minutes}m])) * 8 / 1000000'
        r = self.query(query)
        rate = r.data[0]['value'][1]
        return int(float(rate))
    
    def check_interface_avg_rate(self,
                                 direction: Literal['in', 'out'],
                                 sysname: str, 
                                 ifname:str, 
                                 last_hours: Optional[int] = 24,
                                 last_minutes: Optional[int] = 5,
                                ) -> ReturnResponse:
        '''
        _summary_

        Args:
            direction (Literal[&#39;in&#39;, &#39;out&#39;]): _description_
            sysname (str): _description_
            ifname (str): _description_
            last_hours (Optional[int], optional): _description_. Defaults to 24.
            last_minutes (Optional[int], optional): _description_. Defaults to 5.

        Returns:
            ReturnResponse: _description_
        '''
        if direction == 'in':
            query = f'avg_over_time((rate(snmp_interface_ifHCInOctets{{sysName="{sysname}", ifName="{ifname}"}}[{last_minutes}m]) * 8) [{last_hours}h:]) / 1e6'
        else:
            query = f'avg_over_time((rate(snmp_interface_ifHCOutOctets{{sysName="{sysname}", ifName="{ifname}"}}[{last_minutes}m]) * 8) [{last_hours}h:]) / 1e6'
        r = self.query(query)
        try:
            rate = r.data[0]['value'][1]
            return ReturnResponse(code=0, msg=f"查询 {sysname} {ifname} 最近 {last_hours} 小时平均速率为 {round(float(rate), 2)} Mbit/s", data=round(float(rate), 2))
        except KeyError:
            return ReturnResponse(code=1, msg=f"查询 {sysname} {ifname} 最近 {last_hours} 小时平均速率为 0 Mbit/s")

    def check_interface_max_rate(self,
                                 direction: Literal['in', 'out'],
                                 sysname: str, 
                                 ifname:str, 
                                 last_hours: Optional[int] = 24,
                                 last_minutes: Optional[int] = 5,
                                ) -> ReturnResponse:
        '''
        _summary_

        Args:
            direction (Literal[&#39;in&#39;, &#39;out&#39;]): _description_
            sysname (str): _description_
            ifname (str): _description_
            last_hours (Optional[int], optional): _description_. Defaults to 24.
            last_minutes (Optional[int], optional): _description_. Defaults to 5.

        Returns:
            ReturnResponse: _description_
        '''
        if direction == 'in':
            query = f'max_over_time((rate(snmp_interface_ifHCInOctets{{sysName="{sysname}", ifName="{ifname}"}}[{last_minutes}m]) * 8) [{last_hours}h:]) / 1e6'
        else:
            query = f'max_over_time((rate(snmp_interface_ifHCOutOctets{{sysName="{sysname}", ifName="{ifname}"}}[{last_minutes}m]) * 8) [{last_hours}h:]) / 1e6'
        r = self.query(query)
        try:
            rate = r.data[0]['value'][1]
            return ReturnResponse(code=0, msg=f"查询 {sysname} {ifname} 最近 {last_hours} 小时最大速率为 {round(float(rate), 2)} Mbit/s", data=round(float(rate), 2))
        except KeyError:
            return ReturnResponse(code=1, msg=f"查询 {sysname} {ifname} 最近 {last_hours} 小时最大速率为 0 Mbit/s")

    def check_snmp_port_status(self, sysname: str=None, if_name: str=None, last_minute: int=5, dev_file: str=None) -> ReturnResponse:
        '''
        查询端口状态
        status code 可参考 SNMP 文件 https://mibbrowser.online/mibdb_search.php?mib=IF-MIB

        Args:
            sysname (_type_): 设备名称
            if_name (_type_): _description_
            last_minute (_type_): _description_

        Returns:
            ReturnResponse: 
            code: 0, msg: , data: up,down
        '''
        q = f"""avg_over_time(snmp_interface_ifOperStatus{{sysName="{sysname}", ifName="{if_name}"}}[{last_minute}m])"""
        if self.env == 'dev':
            r = load_dev_file(dev_file)
        else:
            r = self.query(query=q)
        if r.code == 0:
            status_code = int(r.data[0]['value'][1])
            if status_code == 1:
                status = 'up'
            else:
                status = 'down'
            return ReturnResponse(code=0, msg=f"{sysname} {if_name} 最近 {last_minute} 分钟端口状态为 {status}", data=status)
        else:
            return r

    def insert_cronjob_run_status(self, 
                                  app_type: Literal['alert', 'meraki', 'other']='other', 
                                  app: str='', 
                                  status_code: Literal[0, 1]=1, 
                                  comment: str=None, 
                                  schedule_interval: str=None, 
                                  schedule_cron: str=None
                                ) -> ReturnResponse:
        labels = {
            "app": app,
            "env": self.env,
        }
        if app_type:
            labels['app_type'] = app_type
        if comment:
            labels['comment'] = comment
            
        if schedule_interval:
            labels['schedule_type'] = 'interval'
            labels['schedule_interval'] = schedule_interval
            
        if schedule_cron:
            labels['schedule_type'] = 'cron'
            labels['schedule_cron'] = schedule_cron
            
        r = self.insert(metric_name="cronjob_run_status", labels=labels, value=status_code)
        return r
    
    def insert_cronjob_duration_seconds(self, 
                                        app_type: Literal['alert', 'meraki', 'other']='other', 
                                        app: str='', 
                                        duration_seconds: float=None, 
                                        comment: str=None, 
                                        schedule_interval: str=None, 
                                        schedule_cron: str=None
                                    ) -> ReturnResponse:
        labels = {
            "app": app,
            "env": self.env
        }
        if app_type:
            labels['app_type'] = app_type
        if comment:
            labels['comment'] = comment

        if schedule_interval:
            labels['schedule_type'] = 'interval'
            labels['schedule_interval'] = schedule_interval
            
        if schedule_cron:
            labels['schedule_type'] = 'cron'
            labels['schedule_cron'] = schedule_cron
        r = self.insert(metric_name="cronjob_run_duration_seconds", labels=labels, value=duration_seconds)
        return r
    
    def get_vmware_esxhostnames(self, vcenter: str=None) -> list:
        '''
        _summary_
        '''
        esxhostnames = []
        query = f'vsphere_host_sys_uptime_latest{{vcenter="{vcenter}"}}'
        metrics = self.query(query=query).data
        for metric in metrics:
            esxhostname = metric['metric']['esxhostname']
            esxhostnames.append(esxhostname)
        return esxhostnames
    
    def get_vmware_cpu_usage(self, vcenter: str=None, esxhostname: str=None) -> float:
        '''
        _summary_
        '''
        query = f'vsphere_host_cpu_usage_average{{vcenter="{vcenter}", esxhostname="{esxhostname}"}}'
        return self.query(query=query).data[0]['value'][1]
    
    def get_vmware_memory_usage(self, vcenter: str=None, esxhostname: str=None) -> float:
        '''
        _summary_
        '''
        query = f'vsphere_host_mem_usage_average{{vcenter="{vcenter}", esxhostname="{esxhostname}"}}'
        return self.query(query=query).data[0]['value'][1]