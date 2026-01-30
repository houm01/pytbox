#!/usr/bin/env python3
import re
import time
import json
from typing import Literal, Optional, Dict, List, Any, Union
import requests
from ..utils.response import ReturnResponse as OldReturnResponse
from ..utils.load_vm_devfile import load_dev_file

from ..schemas.response import ReturnResponse
from ..schemas.codes import RespCode
from ..schemas.vm_query import VMInstantQueryResponse, VMInstantSeries




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
               value: List[float] = None, timestamp: int = None) -> OldReturnResponse:
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
            # Use session for connection reuse (significantly faster for many inserts)
            response = self.session.post(url, json=data, timeout=self.timeout)
            return OldReturnResponse(code=0, msg=f"数据插入成功，状态码: {response.status_code}, metric_name: {metric_name}, labels: {labels}, value: {value}, timestamp: {timestamp}")
        except requests.RequestException as e:
            return OldReturnResponse(code=1, msg=f"数据插入失败: {e}")

    def insert_many(
        self,
        metric_name: str,
        items: List[Dict[str, Any]],
        batch_size: int = 500,
    ) -> OldReturnResponse:
        """
        Batch insert metrics via VictoriaMetrics /api/v1/import using NDJSON.

        items:
          - labels: Dict[str, Any]
          - value: float|int (optional, default 1)
          - timestamp: int ms (optional, default now; missing timestamps will be auto-filled)
        """
        if not items:
            return OldReturnResponse(
                code=0,
                msg=f"[vm][insert_many] metric [{metric_name}] empty items, skip",
                data={"inserted": 0},
            )

        url = f"{self.url}/api/v1/import"
        inserted = 0

        # Keep timestamps close to "now" and unique when not provided.
        base_ts = int(time.time() * 1000)

        def _normalize_labels(raw: Dict[str, Any]) -> Dict[str, str]:
            if raw is None:
                return {}
            out: Dict[str, str] = {}
            for k, v in raw.items():
                if v is None:
                    out[k] = "None"
                elif isinstance(v, bool):
                    out[k] = str(v)
                else:
                    out[k] = str(v)
            return out

        headers = {"Content-Type": "application/x-ndjson"}

        try:
            for start in range(0, len(items), max(1, batch_size)):
                chunk = items[start : start + max(1, batch_size)]
                lines: List[str] = []
                for i, item in enumerate(chunk):
                    labels = _normalize_labels(item.get("labels", {}))
                    value = item.get("value", 1)
                    ts = item.get("timestamp")
                    if ts is None:
                        ts = base_ts + inserted + i

                    payload = {
                        "metric": {"__name__": metric_name, **labels},
                        "values": [value],
                        "timestamps": [ts],
                    }
                    lines.append(json.dumps(payload, ensure_ascii=False))

                body = ("\n".join(lines) + "\n").encode("utf-8")
                resp = self.session.post(url, data=body, headers=headers, timeout=self.timeout)
                if resp.status_code > 210:
                    return OldReturnResponse(
                        code=1,
                        msg=f"[vm][insert_many][fail] metric [{metric_name}] http={resp.status_code} body={resp.text}",
                        data={"inserted": inserted},
                    )

                inserted += len(chunk)

            return OldReturnResponse(
                code=0,
                msg=f"[vm][insert_many][ok] metric [{metric_name}] inserted={inserted}",
                data={"inserted": inserted},
            )
        except requests.RequestException as e:
            return OldReturnResponse(
                code=1,
                msg=f"[vm][insert_many][fail] metric [{metric_name}] error={e}",
                data={"inserted": inserted},
            )

    def query(self, query: str=None, output_format: Literal['json']=None) -> OldReturnResponse:
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

        resp = OldReturnResponse(code=code, msg=msg, data=data)

        if is_json:
            json_result = json.dumps(resp.__dict__, ensure_ascii=False)
            return json_result
        else:
            return resp
    
    def query_instant(
        self, 
        query: Optional[str] = None
    ) -> ReturnResponse:
        url = f'{self.url}/prometheus/api/v1/query'
        try:
            r = requests.get(url, timeout=self.timeout, params={'query': query})
            r.raise_for_status()
            res_json = r.json()
        except requests.RequestException as e:
            resp = ReturnResponse.fail(
                RespCode.VM_REQUEST_FAILED, 
                msg=f'查询失败: {e}',
                data=None
            )
            return resp
        except ValueError as e:
            resp = ReturnResponse.fail(
                RespCode.VM_BAD_PAYLOAD,
                msg=f"[{query}] VM 返回非 JSON: {e}",
                data=None
            )
            return resp
        
        status = res_json.get('status')
        if status != 'success':
            resp = ReturnResponse.fail(
                RespCode.VM_QUERY_FAILED,
                msg=f"[{query}] 查询失败: {res_json.get('error')}",
                data=res_json
            )
            return resp
        raw_result = res_json.get("data", {}).get("result", [])
        if not raw_result:
            resp = ReturnResponse.no_data(
                msg=f"[{query}] 没有查询到结果",
                data=[]
            )
            return resp
        
        try:
            series_list = [VMInstantSeries(**item) for item in raw_result]
        except ValidationError as e:
            resp = ReturnResponse.fail(
                RespCode.VM_BAD_PAYLOAD,
                msg=f"[{query}] 返回结构不符合预期",
                data=str(e)
            )
            return resp
        
        resp_typed = VMInstantQueryResponse(
            code=int(RespCode.OK),
            msg=f"[{query}] 查询成功!",
            data=series_list
        )
        return resp_typed
        
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

        # resp = OldReturnResponse(code=code, msg=msg, data=data)

        # if is_json:
        #     json_result = json.dumps(resp.__dict__, ensure_ascii=False)
        #     return json_result
        # else:
        #     return resp
    def get_labels(self, metric_name: str) -> OldReturnResponse:
        url = f"{self.url}/api/v1/series?match[]={metric_name}"
        response = requests.get(url, timeout=self.timeout)
        results = response.json()
        if results['status'] == 'success':
            return OldReturnResponse(code=0, msg=f"metric name: {metric_name} 获取到 {len(results['data'])} 条数据", data=results['data'])
        else:
            return OldReturnResponse(code=1, msg=f"metric name: {metric_name} 查询失败")

    def check_ping_result(self, target: str, last_minute: int=10, env: str='prod', dev_file: str='') -> OldReturnResponse:
        '''
        检查ping结果

        Args:
            target (str): 目标地址
            last_minute (int, optional): 最近多少分钟. Defaults to 10.
            env (str, optional): 环境. Defaults to 'prod'.
            dev_file (str, optional): 开发文件. Defaults to ''.

        Returns:
            OldReturnResponse: 
                code = 0 正常, code = 1 异常, code = 2 没有查询到数据, 建议将其判断为正常
        '''
        query = f'min_over_time(ping_result_code{{target="{target}"}}[{last_minute}m])'
        # query = f'avg_over_time((ping_result_code{{target="{target}"}})[{last_minute}m])'
        if self.env == 'dev':
            r = load_dev_file(dev_file)
        else:
            r = self.query(query=query)
        if r.code == 0:
            # print(r.data[0])
            try:
                value = r.data[0]['values'][1]
            except KeyError:
                value = r.data[0]['value'][1]
                
            if value == '0':
                return OldReturnResponse(code=0, msg=f"已检查 {target} 最近 {last_minute} 分钟是正常的!", data=r.data)
            else:
                return OldReturnResponse(code=1, msg=f"已检查 {target} 最近 {last_minute} 分钟是异常的!", data=r.data)
        else:
            return r

    def check_unreachable_ping_result(self, dev_file: str='') -> OldReturnResponse:
        '''
        检查ping结果

        Args:
            target (str): 目标地址
            last_minute (int, optional): 最近多少分钟. Defaults to 10.
            env (str, optional): 环境. Defaults to 'prod'.
            dev_file (str, optional): 开发文件. Defaults to ''.

        Returns:
            OldReturnResponse: 
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
                             sysname: str, 
                             ifname:str, 
                             last_n_minutes: Optional[int] = None,
                             dev_file: str=None
                            ) -> OldReturnResponse:
        """查询指定设备的入方向总流量速率（bps）。

        使用 PromQL 对 `snmp_interface_ifHCInOctets` 进行速率计算并聚合到设备级别，
        将结果从字节每秒转换为比特每秒（乘以 8）。

        Args:
            sysName: 设备 `sysName` 标签值。
            last_minutes: 计算速率的时间窗口（分钟）。未提供时默认使用 5 分钟窗口。

        Returns:
            OldReturnResponse: 查询结果包装。
        """
        if direction == 'in':
            query = f'(rate(snmp_interface_ifHCInOctets{{sysName="{sysname}", ifName="{ifname}"}}[{last_n_minutes}m])) * 8 / 1000000'
        else:
            query = f'(rate(snmp_interface_ifHCOutOctets{{sysName="{sysname}", ifName="{ifname}"}}[{last_n_minutes}m])) * 8 / 1000000'
        
        if dev_file is not None:
            r = load_dev_file(dev_file)
        else:
            r = self.query(query=query)
        
        if r.code == 0:
            return OldReturnResponse(
                code=0, 
                msg=f"{sysname} {ifname} 最近 {last_n_minutes} 分钟 {direction} 方向流量速率为 {int(r.data[0]['value'][1])} Mbit/s", 
                data={
                    'query': query,
                    'data': int(float(r.data[0]['value'][1]))
                }
            )
        else:
            return OldReturnResponse(
                code=1, 
                msg=f"查询 {sysname} {ifname} 最近 {last_n_minutes} 分钟 {direction} 方向流量速率失败, 错误信息: {r.msg}", 
                data={
                    'query': query,
                    'data': None
                }
            )
    
    def check_interface_avg_rate(self,
                                 direction: Literal['in', 'out'],
                                 sysname: str, 
                                 ifname:str, 
                                 last_hours: Optional[int] = 24,
                                 last_minutes: Optional[int] = 5,
                                ) -> OldReturnResponse:
        '''
        _summary_

        Args:
            direction (Literal[&#39;in&#39;, &#39;out&#39;]): _description_
            sysname (str): _description_
            ifname (str): _description_
            last_hours (Optional[int], optional): _description_. Defaults to 24.
            last_minutes (Optional[int], optional): _description_. Defaults to 5.

        Returns:
            OldReturnResponse: _description_
        '''
        if direction == 'in':
            query = f'avg_over_time((rate(snmp_interface_ifHCInOctets{{sysName="{sysname}", ifName="{ifname}"}}[{last_minutes}m]) * 8) [{last_hours}h:]) / 1e6'
        else:
            query = f'avg_over_time((rate(snmp_interface_ifHCOutOctets{{sysName="{sysname}", ifName="{ifname}"}}[{last_minutes}m]) * 8) [{last_hours}h:]) / 1e6'
        r = self.query(query)
        try:
            rate = r.data[0]['value'][1]
            return OldReturnResponse(code=0, msg=f"查询 {sysname} {ifname} 最近 {last_hours} 小时平均速率为 {round(float(rate), 2)} Mbit/s", data=round(float(rate), 2))
        except KeyError:
            return OldReturnResponse(code=1, msg=f"查询 {sysname} {ifname} 最近 {last_hours} 小时平均速率为 0 Mbit/s")

    def check_interface_max_rate(self,
                                 direction: Literal['in', 'out'],
                                 sysname: str, 
                                 ifname:str, 
                                 last_hours: Optional[int] = 24,
                                 last_minutes: Optional[int] = 5,
                                ) -> OldReturnResponse:
        '''
        _summary_

        Args:
            direction (Literal[&#39;in&#39;, &#39;out&#39;]): _description_
            sysname (str): _description_
            ifname (str): _description_
            last_hours (Optional[int], optional): _description_. Defaults to 24.
            last_minutes (Optional[int], optional): _description_. Defaults to 5.

        Returns:
            OldReturnResponse: _description_
        '''
        if direction == 'in':
            query = f'max_over_time((rate(snmp_interface_ifHCInOctets{{sysName="{sysname}", ifName="{ifname}"}}[{last_minutes}m]) * 8) [{last_hours}h:]) / 1e6'
        else:
            query = f'max_over_time((rate(snmp_interface_ifHCOutOctets{{sysName="{sysname}", ifName="{ifname}"}}[{last_minutes}m]) * 8) [{last_hours}h:]) / 1e6'
        r = self.query(query)
        try:
            rate = r.data[0]['value'][1]
            return OldReturnResponse(code=0, msg=f"查询 {sysname} {ifname} 最近 {last_hours} 小时最大速率为 {round(float(rate), 2)} Mbit/s", data=round(float(rate), 2))
        except KeyError:
            return OldReturnResponse(code=1, msg=f"查询 {sysname} {ifname} 最近 {last_hours} 小时最大速率为 0 Mbit/s")

    def check_snmp_port_status(self, sysname: str=None, if_name: str=None, last_minute: int=5, dev_file: str=None) -> OldReturnResponse:
        '''
        查询端口状态
        status code 可参考 SNMP 文件 https://mibbrowser.online/mibdb_search.php?mib=IF-MIB

        Args:
            sysname (_type_): 设备名称
            if_name (_type_): _description_
            last_minute (_type_): _description_

        Returns:
            OldReturnResponse: 
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
            return OldReturnResponse(code=0, msg=f"{sysname} {if_name} 最近 {last_minute} 分钟端口状态为 {status}", data=status)
        else:
            return r

    def insert_cronjob_run_status(self, 
                                  app_type: Literal['alert', 'meraki', 'other']='other', 
                                  app: str='', 
                                  status_code: Literal[0, 1]=1, 
                                  comment: str=None, 
                                  schedule_interval: str=None, 
                                  schedule_cron: str=None
                                ) -> OldReturnResponse:
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
                                    ) -> OldReturnResponse:
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

    def get_snmp_interfaces(self, sysname):
        r = self.query(query=f'snmp_interface_ifOperStatus{{sysName="{sysname}"}}')
        return r
    
    def get_snmp_interface_oper_status(self, 
                                       sysname: str=None, 
                                       ifname: str=None, 
                                       sysname_repr: str=None,
                                       ifname_list: list=[], 
                                       dev_file: str=None
                                    ) -> OldReturnResponse:
        if dev_file is not None:
            r = load_dev_file(dev_file)
        else:
            if ifname_list and sysname_repr:
                ifname_pattern = '|'.join([re.escape(name) for name in ifname_list])
                query = f'snmp_interface_ifOperStatus{{sysName=~"{sysname_repr}", ifName=~"^({ifname_pattern})$"}}'
            else:
                query = f'snmp_interface_ifOperStatus{{sysName="{sysname}", ifName="{ifname}"}}'
            print(query)
            r = self.query(query=query)
        
        return r
    
    def get_viptela_bfd_sessions_up(self, 
                                    sysname: str=None, 
                                    session_up_lt: int=None, 
                                    session_up_gt: int=None, 
                                    last_minute: int=10, 
                                    dev_file: str=None
                                ) -> OldReturnResponse:
        '''
        获取 viptela BFD 会话数

        Args:
            sysname (str, optional): 设备名称. Defaults to None.
            session_up_lt (int, optional): 最近多少分钟内 BFD 会话数小于 session_up_lt. Defaults to None.
            session_up_gt (int, optional): 最近多少分钟内 BFD 会话数大于 session_up_gt. Defaults to None.
            last_minute (int, optional): 最近多少分钟. Defaults to 10.
            dev_file (str, optional): 开发文件. Defaults to None.

        Returns:
            OldReturnResponse:
                code: 0, msg: 状态描述, data:
                    query: 查询语句
                    data: 查询结果列表
                    status: "fault" 或 "normal"
                    status_msg: 状态说明
                    mode: "fault_check" 或 "recovery_check"
                    sysname: 设备名称或 None
                code: 1, msg: 错误信息, data: None
        '''
        if dev_file is not None:
            r = load_dev_file(dev_file)
            results = r.data['data']['result']
            data = []
            for result in results:
                data.append(
                    {
                        "agent_host": result['metric']['agent_host'],
                        "sysname": result['metric']['sysName'],
                        "value": int(result['value'][1])
                    }
                )
            return OldReturnResponse(code=r.code, msg=f"获取到 {len(data)} 条数据", data=data)
        else:
            if sysname is None:
                if session_up_lt is not None:
                    query = f'max_over_time(vedge_snmp_bfdSummaryBfdSessionsUp[{last_minute}m]) < {session_up_lt}'
                elif session_up_gt is not None:
                    query = f'max_over_time(vedge_snmp_bfdSummaryBfdSessionsUp[{last_minute}m]) > {session_up_gt}'
                else:
                    return OldReturnResponse(code=1, msg="sysname 和 session_up_lt 或 session_up_gt 不能同时为空")
            else:
                query = f'max_over_time(vedge_snmp_bfdSummaryBfdSessionsUp{{sysName="{sysname}"}}[{last_minute}m]) > {session_up_gt}'
                
            r = self.query(query=query)
            results = r.data

            data = []
            if isinstance(results, dict) and not results['data'].get('result'):
                return OldReturnResponse(code=1, msg=f"满足条件的有0条数据", data=data)
            for result in results:
                data.append(
                    {
                        "agent_host": result['metric']['agent_host'],
                        "sysname": result['metric']['sysName'],
                        "value": int(result['value'][1])
                    }
                )
            return OldReturnResponse(code=r.code, msg=f"满足条件的有 {len(data)} 条", data=data)

    def get_viptela_bfd_session_list_state(self, sysname: str=None, last_minute: int=30, dev_file: str=None) -> OldReturnResponse:
        '''
        获取 viptela BFD 会话列表状态

        Args:
            sysname (str, optional): 设备名称. Defaults to None.
            last_minute (int, optional): 最近多少分钟. Defaults to 30.
            dev_file (str, optional): 开发文件. Defaults to None.

        Returns:
            OldReturnResponse: 
        '''
        if dev_file is not None:
            query = None
            r = load_dev_file(dev_file)
        else:
            query = f"""limitk(12,
                sort_desc(
                    max_over_time(
                        vedge_snmp_bfd_bfdSessionsListState{{sysName="{sysname}"}}[{last_minute}m]
                    )
                )
            )"""
            r = self.query(query=query)

        if r.code == 0:
            results = r.data
            data = []
            for result in results:
                data.append(result['metric'] | {'value': result['value'][1]})
            return OldReturnResponse(code=0, msg=f"获取到 {len(data)} 条数据", data={'query': query, 'data': data})
    
    def get_apc_input_status(self, 
                             sysname: str=None,
                             last_minutes: int=5,
                             threshold: int=3,
                             dev_file: str=None) -> OldReturnResponse:
        '''
        获取 UPS 输入状态

        Args:
            sysname (str, optional): 设备名称. Defaults to None.
            last_minutes (int, optional): 最近多少分钟. Defaults to 5.
            threshold (int, optional): 连续多少分钟小于阈值. Defaults to 3.
            dev_file (str, optional): 开发文件. Defaults to None.

        Returns:
            OldReturnResponse: 
                code: 0, msg: 获取到多少条数据, data: 数据列表
                code: 1, msg: 错误信息, data: None
        '''
        if sysname is None:
            # 全量查询：近 last_minutes 分钟内，累计低电压点数达到阈值判定为中断
            query = (
                "count_over_time((snmp_upsInput_upsAdvInputLineVoltage < 1)"
                f"[{last_minutes}m:1m]) >= {threshold}"
            )
        else:
            # 单设备查询：近 last_minutes 分钟内全部 > 1 才算恢复
            query = (
                "count_over_time((snmp_upsInput_upsAdvInputLineVoltage"
                f'{{sysName="{sysname}"}} <= 1)[3m:1m]) == 0'
            )
        if dev_file is not None:
            r = load_dev_file(dev_file)
        else:
            r = self.query(query=query)
        print(r)
        if r.code in (0, 2):
            data = r.data or []
            print(data)

            if sysname is None and not data['data']['result']:
                status = "normal"
                status_msg = "not found ups fault device"
                mode = "fault_check"
            elif sysname is None:
                status = "fault" if len(data) > 0 else "normal"
                status_msg = "存在中断设备" if len(data) > 0 else "未发现中断设备"
                mode = "fault_check"
            else:
                status = "normal" if len(data) > 0 else "fault"
                status_msg = "市电已恢复" if len(data) > 0 else "市电仍中断"
                mode = "recovery_check"
            return OldReturnResponse(
                code=0,
                msg=status_msg,
                data={
                    'query': query,
                    'data': data,
                    'status': status,
                    'status_msg': status_msg,
                    'mode': mode,
                    'sysname': sysname,
                },
            )
        else:
            return OldReturnResponse(code=r.code, msg=r.msg, data={'query': query, 'data': None})

    def get_apc_battery_replace_status(self, 
                             sysname: str=None,
                             last_minutes: int=5,
                             threshold: int=3,
                             dev_file: str=None) -> OldReturnResponse:
        '''
        获取 UPS 电池更换状态

        Args:
            sysname (str, optional): 设备名称. Defaults to None.
            last_minutes (int, optional): 最近多少分钟. Defaults to 5.
            threshold (int, optional): 连续多少分钟小于阈值. Defaults to 3.
            dev_file (str, optional): 开发文件. Defaults to None.

        Returns:
            OldReturnResponse:
                code: 0, msg: 状态描述, data:
                    query: 查询语句
                    data: 查询结果列表
                    status: "fault" 或 "normal"
                    status_msg: 状态说明
                    mode: "fault_check" 或 "recovery_check"
                    sysname: 设备名称或 None
                code: 1, msg: 错误信息, data: None
        '''
        if sysname is None:
            # 全量查询：近 last_minutes 分钟内，累计需要更换点数达到阈值判定为异常
            query = (
                "count_over_time((snmp_upsBattery_upsAdvBatteryReplaceIndicator == 2)"
                f"[{last_minutes}m:1m]) >= {threshold}"
            )
        else:
            # 单设备查询：近 threshold 分钟内没有更换点才算恢复
            query = (
                "count_over_time((snmp_upsBattery_upsAdvBatteryReplaceIndicator"
                f'{{sysName="{sysname}"}} == 2)[{threshold}m:1m]) == 0'
            )
            
        if dev_file is not None:
            r = load_dev_file(dev_file)
        else:
            r = self.query(query=query)
        
        if r.code == 0:
            data = r.data or []
            if sysname is None:
                status = "fault" if len(data) > 0 else "normal"
                status_msg = "存在需要更换电池的设备" if len(data) > 0 else "未发现需要更换电池的设备"
                mode = "fault_check"
            else:
                status = "normal" if len(data) > 0 else "fault"
                status_msg = "电池更换告警已恢复" if len(data) > 0 else "电池更换告警仍存在"
                mode = "recovery_check"
            return OldReturnResponse(
                code=r.code,
                msg=status_msg,
                data={
                    'query': query,
                    'data': data,
                    'status': status,
                    'status_msg': status_msg,
                    'mode': mode,
                    'sysname': sysname,
                },
            )
        else:
            return OldReturnResponse(code=r.code, msg=r.msg, data={'query': query, 'data': None})
    
    def get_system_uptime(self, sysname: str=None, uptime_lt_minute: int=None, dev_file: str=None) -> OldReturnResponse:
        if sysname is None and uptime_lt_minute is not None:
            query = f'snmp_sysUpTime < {uptime_lt_minute * 60}'
        else:
            query = f'snmp_sysUpTime{{sysName="{sysname}"}}'
            
        if dev_file is not None:
            r = load_dev_file(dev_file)
        else:
            r = self.query(query=query)
        
        if r.code == 0:
            return OldReturnResponse(code=r.code, msg=f"获取到 {len(r.data)} 条数据", data={'query': query, 'data': r.data, 'uptime_minute': int(float(r.data[0]['value'][1]) / 60)})
        else:
            return OldReturnResponse(code=r.code, msg=r.msg, data={'query': query, 'data': None})