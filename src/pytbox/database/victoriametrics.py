#!/usr/bin/env python3

import json
from typing import Literal, Optional
import requests
from ..utils.response import ReturnResponse
from ..utils.load_vm_devfile import load_dev_file


class VictoriaMetrics:
    
    def __init__(self, url: str='', timeout: int=3) -> None:
        self.url = url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
    def query(self, query: str, output_format: Literal['json']=None) -> ReturnResponse:
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
        if target:
            # 这里需要在字符串中保留 {}，同时插入 target，可以用双大括号转义
            query = f"ping_result_code{{target='{target}'}}"
        else:
            query = "ping_result_code"
        
        if last_minute:
            query = query + f"[{last_minute}m]"
        
        if env == 'dev':
            r = load_dev_file(dev_file)
        else:
            r = self.query(query=query)
 
        if r.code == 0:
            values = r.data[0]['values']
            if len(values) == 2 and values[1] == "0":
                code = 0
                msg = f"已检查 {target} 最近 {last_minute} 分钟是正常的!"
            else:
                
                if all(str(item[1]) == "1" for item in values):
                    code = 1
                    msg = f"已检查 {target} 最近 {last_minute} 分钟是异常的!"
                else:
                    code = 0
                    msg = f"已检查 {target} 最近 {last_minute} 分钟是正常的!"
        elif r.code == 2:
            code = 2
            msg = f"没有查询到 {target} 最近 {last_minute} 分钟的ping结果!"
        
        try:
            data = r.data[0]
        except KeyError:
            data = r.data
        
        return ReturnResponse(code=code, msg=msg, data=data)

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