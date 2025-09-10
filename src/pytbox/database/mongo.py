#!/usr/bin/env python3

import pymongo
from ..utils.timeutils import TimeUtils
from pytbox.utils import timeutils

class Mongo:
    '''
    当前主要使用的类
    '''
    def __init__(self, host: str=None, port: int=27017, username: str=None, password: str=None, auto_source: str=None, db_name: str='automate', collection: str=None):
        self.client = self._create_client(host, port, username, password, auto_source)
        self.collection = self.client[db_name][collection]
    
    def _create_client(self, host, port, username, password, auto_source):
        '''
        创建客户端
        '''
        return pymongo.MongoClient(host=host,
                    port=port,
                    username=username,
                    password=password,
                    authSource=auto_source)
    
    
    def check_alarm_exist(self, event_type, event_content) -> bool:
        '''
        _summary_

        Args:
            event_content (_type_): 告警内容

        Returns:
            bool: 如果为 True, 表示允许插入告警
        '''
        if event_type == 'trigger':
            query = { "event_content": event_content }
            fields = {"event_name": 1, "event_time": 1, "resolved_time": 1}
            result = self.collection.find(query, fields).sort({ "_id": pymongo.DESCENDING }).limit(1)
            if self.collection.count_documents(query) == 0:
                return True
            else:
                for doc in result:
                    if 'resolved_time' in doc:
                        # 当前没有告警, 可以插入数据
                        return True
        elif event_type == 'resolved':
            return True

    def query_alert_not_resolved(self, event_name: str=None):
        query = {
            "$or": [
                {"resolved_time": { "$exists": False }}
            ]
        }
        if event_name:
            query['event_name'] = event_name
        return self.collection.find(query)

    def recent_alerts(self, event_content: str) -> str:
        '''
        获取最近 10 次告警

        Args:
            alarm_content (str): _description_

        Returns:
            str: _description_
        '''

        query = {
            "event_content": event_content,
            'resolved_time': {
                '$exists': True,  # 字段必须存在
            }
        }
        fields = {"_id": 0, 'event_time': 1, 'resolved_time': 1}
        results = self.collection.find(query, fields).sort('event_time', -1)
        
        alarm_list = []
        for result in results:
            duration_minute = '持续 ' + str(int((result['resolved_time'] - result['event_time']).total_seconds() / 60)) + ' 分钟'
            alarm_list.append('触发时间: ' + TimeUtils.convert_timeobj_to_str(timeobj=result['event_time']) + ' ' + duration_minute)

        alarm_str = '\n'.join(alarm_list)
        
        alarm_str_display_threshold = 10
        
        if len(alarm_list) > alarm_str_display_threshold:
            # 如果告警超过 10 个
            alarm_counter = alarm_str_display_threshold
            alarm_str = '\n'.join(alarm_list[:alarm_str_display_threshold])
        else:
            # 如果不超过 10 个
            alarm_counter = len(alarm_list)
            alarm_str = '\n'.join(alarm_list)
            
        return '该告警出现过' + str(len(alarm_list)) + f'次\n最近 {alarm_counter} 次告警如下: \n' + alarm_str
    