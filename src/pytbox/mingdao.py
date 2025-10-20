#!/usr/bin/env python3

from typing import Literal, Type

import requests

from .utils.response import ReturnResponse


class Mingdao:
    '''
    _summary_
    '''
    def __init__(self, app_key: str=None, sign: str=None, timeout: int=5):
        self.base_url = "https://api.mingdao.com"
        self.headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'
        }
        self.timeout = timeout
        self.app_key = app_key
        self.sign = sign

    def _build_api_request(self, api_url: str, method: Literal['GET', 'POST'], params: dict=None, body: dict=None, api_version: Literal['v1', 'v2']='v2'):
        body['appKey'] = self.app_key
        body['sign'] = self.sign
        if not api_url.startswith('/'):
            url = f'{self.base_url}/{api_version}/{api_url}'
        else:
            url = f'{self.base_url}/{api_version}{api_url}'
        params = {
            "appKey": self.app_key,
            "sign": self.sign,
        }
        return requests.request(method, url, params=params, headers=self.headers, json=body, timeout=self.timeout)
    
    def get_app_info(self) -> ReturnResponse:
        '''
        _summary_

        Returns:
            ReturnResponse: _description_
        '''
        r = self._build_api_request(api_url='/open/app/get', method='GET', body={}, api_version='v1')
        return ReturnResponse(code=0, msg='获取应用信息成功', data=r.json())
    
    def get_work_sheet_info(self, worksheet_id: str=None, table_name: str=None, worksheet_name: str=None):
        if worksheet_name:
            worksheet_id = self.get_work_sheet_id_by_name(table_name=table_name, worksheet_name=worksheet_name)
        
        r = self._build_api_request(
            api_url='open/worksheet/getWorksheetInfo',
            method='POST',
            body={
                "worksheetId": worksheet_id,
            }
        )
        return r.json()
    
    def get_project_info(self, worksheet_id: str, keywords: str):
        r = self._build_api_request(
            api_url='open/worksheet/getFilterRows',
            method='POST',
            body={
                "pageIndex": 1,
                "pageSize": 100,
                "worksheetId": worksheet_id,
                "keyWords": keywords,
            }
        )
        return r.json()
    
    def get_work_sheet_id_by_name(self, table_name: str, worksheet_name: str, child_section: bool=False):
        r = self.get_app_info()        
        for i in r.data['data']['sections']:
            if table_name == i['name']:
                if child_section:
                    for child in i['childSections'][0]['items']:
                        if child['name'] == worksheet_name:
                            return child['id']
                else:
                    for item in i['items']:
                        if item['name'] == worksheet_name:
                            return item['id']

    def get_control_id(self, table_name: str=None, worksheet_name: str=None, control_name: str=None):
        r = self.get_work_sheet_info(table_name=table_name, worksheet_name=worksheet_name)
        for control in r['data']['controls']:
            if control['controlName'] == control_name:
                return control['controlId']
        return None
    
    def get_value(self, table_name: str=None, worksheet_name: str=None, control_name: str=None, value_name: str=None):
        control_id = self.get_control_id(table_name=table_name, worksheet_name=worksheet_name, control_name=control_name)
  
        r = self._build_api_request(
            api_url='open/worksheet/getFilterRows',
            method='POST',
            body={
                "pageIndex": 1,
                "pageSize": 100,
                "worksheetId": self.get_work_sheet_id_by_name(table_name=table_name, worksheet_name=worksheet_name),
                # "filters": filters
            }
        )
        for row in r.json()['data']['rows']:
            if row[control_id] == value_name:
                return row['rowid']

    def get_work_record(self, 
                        worksheet_id: str=None,
                        project_control_id: str=None,
                        project_value: str=None,
                        complete_date_control_id: str=None,
                        complete_date: Literal['Today', '上个月', 'Last7Day', 'Last30Day']=None,
                        parse_control_id: bool=False,
                        page_size: int=100,
                    ):
        
        filters = []
        if project_value:
            filters.append({
                "controlId": project_control_id,
                "dataType": 29,
                "spliceType": 1,
                "filterType": 24,
                "dateRange": 0,
                "dateRangeType": 0,
                "value": "",
                "values": [
                    project_value
                ],
                "minValue": "",
                "maxValue": ""
            })
        
        if complete_date:
            if complete_date == '上个月':
                data_range = 8
            elif complete_date == 'Today':
                data_range = 1
            elif complete_date == 'Last7Day':
                data_range = 21
            else:
                data_range = 1
            
            filters.append({
                "controlId": complete_date_control_id,
                "dataType": 15,
                "spliceType": 1,
                "filterType": 17,
                "dateRange": data_range,
            })
        r = self._build_api_request(
            api_url='open/worksheet/getFilterRows',
            method='POST',
            body={
                "pageIndex": 1,
                "pageSize": page_size,
                "worksheetId": worksheet_id,
                "filters": filters
            }
        )
        return r.json()