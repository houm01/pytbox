#!/usr/bin/env python3

import pymongo


class Mongo:
    '''
    当前主要使用的类
    '''
    def __init__(self, host, port, username, password, auto_source, db_name: str='automate', collection: str=None):
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

