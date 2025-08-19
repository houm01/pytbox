#!/usr/bin/env python3

import requests
from ..utils.response import ReturnResponse


class VictoriaMetrics:
    
    def __init__(self, url: str='', timeout: int=3) -> None:
        self.url = url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
    def query(self, query: str) -> ReturnResponse:
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
        if r.json().get("status") == "success":
            if r.json()['data']['result']:
                return ReturnResponse(code=0, msg=f"[{query}] 查询成功!", data=r.json()['data']['result'])
            else:
                return ReturnResponse(code=2, msg=f"[{query}] 没有查询到结果", data=r.json())
        else:
            return ReturnResponse(code=1, msg=f"[{query}] 查询失败: {r.json().get('error')}", data=r.json())
    
    def check_ping_result(self, target: str, last_minute: int=10) -> ReturnResponse:
        '''
        检查ping结果
        '''
        if target:
            # 这里需要在字符串中保留 {}，同时插入 target，可以用双大括号转义
            query = f"ping_result_code{{target='{target}'}}"
        else:
            query = "ping_result_code"
        
        if last_minute:
            query = query + f"[{last_minute}m]"
        
        r = self.query(query=query)
        if r.code == 0:
            values = r.data[0]['values']
            if len(values) == 2 and values[1] == "0":
                code = 0
                msg = f"已检查 {target} 最近 {last_minute} 分钟是正常的!"
            else:
                if all(str(item[1]) == "1" for item in values):
                    code = 2
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