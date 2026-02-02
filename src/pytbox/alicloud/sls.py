#!/usr/bin/env python3

from typing import Literal
# 引入sls包。
from aliyun.log import GetLogsRequest, LogItem, PutLogsRequest
from aliyun.log import LogClient as SlsLogClient
from aliyun.log.auth import AUTH_VERSION_4



class AliCloudSls:
    '''
    pip install -U aliyun-log-python-sdk
    '''
    def __init__(self, access_key_id: str=None, access_key_secret: str=None, project: str=None, logstore: str=None, env: str='prod'):
        # 日志服务的服务接入点
        """
        初始化对象。

        Args:
            access_key_id: 资源 ID。
            access_key_secret: access_key_secret 参数。
            project: project 参数。
            logstore: logstore 参数。
            env: env 参数。
        """
        self.endpoint = "cn-shanghai.log.aliyuncs.com"
        # 创建 LogClient 实例，使用 V4 签名，根据实际情况填写 region，这里以杭州为例
        self.client = SlsLogClient(self.endpoint, access_key_id, access_key_secret, auth_version=AUTH_VERSION_4, region='cn-shanghai')
        self.project = project
        self.logstore = logstore
        self.env = env

    def get_logs(self, project_name, logstore_name, query, from_time, to_time): 
        """
        获取logs。

        Args:
            project_name: project_name 参数。
            logstore_name: logstore_name 参数。
            query: query 参数。
            from_time: from_time 参数。
            to_time: to_time 参数。

        Returns:
            Any: 返回值。
        """
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
        """
        执行 put logs 相关逻辑。

        Args:
            topic: topic 参数。
            level: level 参数。
            msg: msg 参数。
            app: app 参数。
            caller_filename: caller_filename 参数。
            caller_lineno: caller_lineno 参数。
            caller_function: caller_function 参数。
            call_full_filename: call_full_filename 参数。

        Returns:
            Any: 返回值。
        """
        log_group = []
        log_item = LogItem()
        contents = [
            ('env', self.env),
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
        r = self.client.put_logs(request)
        return r
        
    def put_logs_for_meraki(self, alert):
        """
        执行 put logs for meraki 相关逻辑。

        Args:
            alert: alert 参数。

        Returns:
            Any: 返回值。
        """
        log_group = []
        log_item = LogItem()
        contents = alert
        log_item.set_contents(contents)
        log_group.append(log_item)
        request = PutLogsRequest(self.project, self.logstore, "", "", log_group, compress=False)
        self.client.put_logs(request)
        

if __name__ == "__main__":
    pass
