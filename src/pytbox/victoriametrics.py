#!/usr/bin/env python3

import requests
from .utils.response import ReturnResponse


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
            return ReturnResponse(code=0, msg=f"[{query}] 查询成功!", data=r.json()['data']['result'])
        else:
            return ReturnResponse(code=1, msg=f"[{query}] 查询失败: {r.json().get('error')}", data=r.json())