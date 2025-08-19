#!/usr/bin/env python3

from typing import Literal
# 引入sls包。
from aliyun.log import GetLogsRequest, LogItem, PutLogsRequest
from aliyun.log import LogClient as SlsLogClient
from aliyun.log.auth import AUTH_VERSION_4
from ..utils.env import check_env



class AliCloudSls:

    def __init__(self, access_key_id: str=None, access_key_secret: str=None, project: str, logstore: str):
        # 日志服务的服务接入点
        self.endpoint = "cn-shanghai.log.aliyuncs.com"
        # 创建 LogClient 实例，使用 V4 签名，根据实际情况填写 region，这里以杭州为例
        self.client = SlsLogClient(self.endpoint, access_key_id, access_key_secret, auth_version=AUTH_VERSION_4, region='cn-shanghai')
        self.project = project
        self.logstore = logstore

    def get_logs(self, project_name, logstore_name, query, from_time, to_time): 
        logstore_index = {'line': {
            'token': [',', ' ', "'", '"', ';', '=', '(', ')', '[', ']', '{', '}', '?', '@', '&', '<', '>', '/', ':', '\n', '\t',
                    '\r'], 'caseSensitive': False, 'chn': False}, 'keys': {'dev': {'type': 'text',
                                                                                    'token': [',', ' ', "'", '"', ';', '=',
                                                                                            '(', ')', '[', ']', '{', '}',
                                                                                            '?', '@', '&', '<', '>', '/',
                                                                                            ':', '\n', '\t', '\r'],
                                                                                    'caseSensitive': False, 'alias': '',
                                                                                    'doc_value': True, 'chn': False},
                                                                            'id': {'type': 'long', 'alias': '',
                                                                                    'doc_value': True}}, 'log_reduce': False,
            'max_text_len': 2048}

        # from_time和to_time表示查询日志的时间范围，Unix时间戳格式。
        # from_time = int(time.time()) - 60
        # to_time = time.time() + 60
        # # 通过SQL查询日志。
        # def get_logs():
        # print("ready to query logs from logstore %s" % logstore_name)
        request = GetLogsRequest(project_name, logstore_name, from_time, to_time, query=query)
        response = self.client.get_logs(request)
        for log in response.get_logs():
            yield log.contents

    def put_logs(self, 
                 topic: Literal['meraki_alert', 'program']='program', 
                 level: Literal['INFO', 'WARN']='INFO', 
                 msg: str=None, 
                 app: str=None, 
                 caller_filename: str=None, 
                 caller_lineno: int=None, 
                 caller_function: str=None, 
                 call_full_filename: str=None
            ):
        log_group = []
        log_item = LogItem()
        contents = [
            ('env', check_env()),
            ('level', level),
            ('app', app),
            ('msg', msg),
            ('caller_filename', caller_filename),
            ('caller_lineno', str(caller_lineno)),
            ('caller_function', caller_function),
            ('call_full_filename', call_full_filename)
        ]
        log_item.set_contents(contents)
        log_group.append(log_item)
        request = PutLogsRequest(self.project, self.logstore, topic, "", log_group, compress=False)
        self.client.put_logs(request)
    
    def put_logs_for_meraki(self, alert):
        log_group = []
        log_item = LogItem()
        contents = alert
        log_item.set_contents(contents)
        log_group.append(log_item)
        request = PutLogsRequest(self.project, self.logstore, "", "", log_group, compress=False)
        self.client.put_logs(request)
        

if __name__ == "__main__":
    pass