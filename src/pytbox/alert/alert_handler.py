#!/usr/bin/env python3


import uuid
from typing import Literal
from ..database.mongo import Mongo
from ..feishu.client import Client as FeishuClient
from ..dida365 import Dida365
from ..utils.timeutils import TimeUtils


class AlertHandler:
    
    def __init__(self, 
                 config: dict=None,
                 mongo_client: Mongo=None,
                 feishu_client: FeishuClient=None,
                 dida_client: Dida365=None
            ):
        self.config = config
        self.mongo = mongo_client
        self.feishu = feishu_client
        self.dida = dida_client

    def send_alert(self, 
                 event_id: str=None,
                 event_type: Literal['trigger', 'resolved'] ='trigger',
                 event_time: str=None,
                 event_name: str=None,
                 event_content: str=None,
                 entity_name: str=None,
                 priority: Literal['critical', 'high', 'warning']='high',
                 resolved_expr: str=None,
                 suggestion: str='',
                 troubleshot: str='暂无',
                 mongo_id: str=None
                ):
        
        if not event_id:
            event_id = str(uuid.uuid4())
        if not event_time:
            event_time = TimeUtils.get_now_time_mongo()
    
        if self.mongo.check_alarm_exist(event_type=event_type, event_content=event_content):
            if event_type == "trigger":
                self.mongo.collection.insert_one(
                    {
                        'event_id': event_id,
                        'event_type': event_type,
                        'event_name': event_name,
                        'event_time': event_time,
                        'event_content': event_content,
                        'entity_name': entity_name,
                        'priority': priority,
                        'resolved_expr': resolved_expr,
                        'suggestion': suggestion,
                        'troubleshot': troubleshot,
                    }
                )
            elif event_type == "resolved":
                filter_doc = {"_id": mongo_id}
                update = {"$set": { "resolved_time": event_time}}
                self.mongo.collection.update_one(filter_doc, update)
                alarm_time = self.mongo.collection.find_one(filter_doc, {'event_time': 1})['event_time']
    
            content = [
                f'**事件名称**: {event_name}',
                f'**告警时间**: {TimeUtils.convert_timeobj_to_str(timeobj=event_time, timezone_offset=0) if event_type == "trigger" else TimeUtils.convert_timeobj_to_str(timeobj=alarm_time, timezone_offset=8)}',
                f'**事件内容**: {event_content}',
                f'**告警实例**: {entity_name}',
                f'**建议**: {suggestion}',
                f'**故障排查**: {troubleshot}',
                f'**历史告警**: {self.mongo.recent_alerts(event_content=event_content)}'
            ]
            
            if event_type == "resolved":
                content.insert(2, f'**恢复时间**: {TimeUtils.convert_timeobj_to_str(event_time, timezone_offset=0)}')
    
            if self.config['feishu']['enable_alert']:
                self.feishu.extensions.send_message_notify(
                    color='red' if event_type == "trigger" else 'green',
                    title=event_content,
                    priority=priority,
                    sub_title="",
                    content='\n'.join(content)
                )
            
            if self.config['dida']['enable_alert']:
                if event_type == "trigger":
                    res = self.dida.task_create(
                        
                        project_id=self.config['dida']['alert_project_id'],
                        title=event_content,
                        content='\n'.join(content),
                        tags=['L-监控告警', priority]
                    )
                    dida_task_id = res.data.get("id")
                    self.mongo.collection.update_one(
                        {
                            "event_id": event_id
                        },
                        {
                            "$set": {
                                "dida_task_id": dida_task_id
                            }
                        }
                    )
                else:
                    task_id = self.mongo.collection.find_one(filter_doc, {'dida_task_id': 1})['dida_task_id']
                    self.dida.task_update(
                        task_id=task_id,
                        project_id=self.config['dida']['alert_project_id'], 
                        content=f'\n**恢复时间**: {TimeUtils.convert_timeobj_to_str(timeobj=event_time, timezone_offset=0)}'
                    )
                    self.dida.task_complete(task_id=task_id, project_id=self.config['dida']['alert_project_id'])
                    
                
            if self.config['wecom']['enable']:
                pass