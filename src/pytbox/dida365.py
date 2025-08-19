#!/usr/bin/env python3

"""滴答清单API客户端。

此模块提供了与滴答清单API交互的功能，包括认证和基本操作。
"""
import re
import json
from typing import Dict, Any, Literal, Union
from dataclasses import dataclass
import requests
from datetime import datetime
from .utils.response import ReturnResponse


@dataclass
class Task:
    task_id: str
    project_id: str
    title: str
    content: str
    desc: str
    start_date: str
    due_date: str
    priority: int
    status: int
    tags: list
    completed_time: str
    assignee: int


class ProcessReturnResponse:    
    @staticmethod
    def status(status):
        if status == 0:
            return '进行中'
        elif status == 2:
            return '已完成'
        else:
            return '未识别'

    @staticmethod
    def priority(priority):
        if priority == 1:
            return '低优先级'
        elif priority == 3:
            return '中优先级'
        elif priority == 5:
            return '高优先级'
        else:
            return '未识别'


class Dida365:
    """滴答清单API客户端类。
    
    处理滴答清单API的认证和操作。
    
    Attributes:
        config: 滴答清单配置实例
        access_token: 访问令牌
        refresh_token: 刷新令牌
    """
    
    def __init__(self, access_token: str, cookie: str) -> None:
        """初始化客户端。
        
        Args:
            access_token: 滴答清单配置实例
        """
        self.access_token = access_token
        self.base_url = 'https://api.dida365.com'
        self.cookie = cookie
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        self.cookie_headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Cookie": self.cookie
        }
        self.timeout = 10

    def request(self, api_url: str=None, method: str='GET', payload: dict={}) -> ReturnResponse:
        """发送请求。
        
        Args:
            url: 请求URL
            method: 请求方法
        """
        
        url = f"{self.base_url}{api_url}"
        response = requests.request(
            method=method,
            url=url, 
            headers=self.headers,
            data=json.dumps(payload),
            timeout=3
        )
        
        if response.status_code == 200:
            if 'complete' in api_url:
                return ReturnResponse(code=0, msg='success', data=None)
            else:
                try:
                    return ReturnResponse(code=0, msg='success', data=response.json())
                except Exception:
                    return ReturnResponse(code=1, msg='warning', data=response)
        else:
            return ReturnResponse(code=1, msg='error', data=response.json())

    def task_list(self, project_id: str, enhancement: bool=True):
        """获取任务列表。
        
        Returns:
            List[Dict[str, Any]]: 任务列表
            
        Raises:
            requests.exceptions.RequestException: 请求失败时抛出
            ValueError: 没有访问令牌时抛出
        """
        if enhancement:
            tasks = requests.request(
                method='GET', 
                url=f'https://api.dida365.com/api/v2/project/{project_id}/tasks', 
                headers=self.cookie_headers, 
                timeout=3
            ).json()
            for task in tasks:
                yield Task(task_id=task.get('id'),
                        project_id=task.get('projectId'),
                        title=task.get('title'),
                        content=task.get('content'),
                        desc=task.get('desc'),
                        start_date=task.get('startDate'),
                        due_date=task.get('dueDate'),
                        priority=ProcessReturnResponse.priority(task.get('priority')),
                        status=ProcessReturnResponse.status(task.get('status')),
                        tags=task.get('tags'),
                        completed_time=task.get('completedTime'),
                        assignee=task.get('assignee'))
        else:
            tasks = self.request(api_url=f"/open/v1/project/{project_id}/data", method="GET")['tasks']
            for task in tasks:
                yield Task(task_id=task.get('id'),
                        project_id=task.get('projectId'),
                        title=task.get('title'),
                        content=task.get('content'),
                        desc=task.get('desc'),
                        start_date=task.get('startDate'),
                        due_date=task.get('dueDate'),
                        priority=ProcessReturnResponse.priority(task.get('priority')),
                        status=ProcessReturnResponse.status(task.get('status')),
                        tags=task.get('tags'),
                        completed_time=task.get('completedTime'),
                        assignee=task.get('assignee'))

    def task_create(self,
               project_id,
               title :str,
               content :str=None, 
               tags :list=None, 
               priority :Literal[1, 3, 5]=1,
               start_date: datetime=datetime.utcnow(),
               start_time_offset: bool=True,
               due_date: str=None,
               kind: Union[None, Literal["NOTE"], str] = 'TEXT',
               assignee: int=None,
               reminder: bool=True):
        '''
        _summary_

        Args:
            project_id (_type_): _description_
            title (str): _description_
            content (str, optional): _description_. Defaults to None.
            tags (list, optional): _description_. Defaults to None.
            priority (Literal[1, 3, 5], optional): _description_. Defaults to 1.
            start_date (datetime, optional): 传入 utc 时区的时间对象. Defaults to datetime.utcnow().
            due_date (str, optional): _description_. Defaults to None.
            kind (Union[None, Literal[&quot;NOTE&quot;], str], optional): _description_. Defaults to 'TEXT'.
            assignee (int, optional): _description_. Defaults to None.
            reminder (bool, optional): _description_. Defaults to True.
        '''
        # 如果存在start_date，将其增加3分钟
        if isinstance(start_date, datetime):
            if start_time_offset:
                if start_date.minute + 3 >= 60:
                    minute = 59
                else:
                    minute = start_date.minute + 3
                start_date_offset = start_date.replace(minute=minute)
                start_date_format = start_date_offset.strftime('%Y-%m-%dT%H:%M:%S.000+0000')
            else:
                start_date_format = start_date.strftime('%Y-%m-%dT%H:%M:%S.000+0000')
        else:
            start_date_format = start_date.strftime('%Y-%m-%dT%H:%M:%S.000+0000')
 
        payload = {
                    "projectId": project_id,
                    "priority": priority,
                    "assignee": str(assignee),
                    # "startDate": start_date_format,
                    "title": title,
                    "timeZone": "Asia/Shanghai",
                    "kind": kind,
                    "content": content,
            }

        payload['startDate'] = start_date_format
        
        if isinstance(due_date, datetime):
            due_date_format = due_date.strftime('%Y-%m-%dT%H:%M:%S.000+0000')
            payload['dueDate'] = due_date_format
        
        if reminder:
            payload["reminders"] = [
                "TRIGGER:PT0S"
            ]
        if tags:
            payload['tags'] = tags
            
        return self.request(api_url="/open/v1/task", method="POST", payload=payload)

    def task_complete(self, project_id: str, task_id: str):
        """完成任务。
        
        Args:
            project_id: 项目ID
            task_id: 任务ID
        """
        return self.request(api_url=f"/open/v1/project/{project_id}/task/{task_id}/complete", method="POST")

    def task_get(self, project_id, task_id):
        return self.request(api_url = f'/open/v1/project/{project_id}/task/{task_id}')

    def task_comments(self, project_id: str, task_id: str):
        return requests.request(
            method='GET',
            url=f'https://api.dida365.com/api/v2/project/{project_id}/task/{task_id}/comments',
            headers=self.cookie_headers,
            timeout=3
        ).json()

    def task_update(self, project_id: str=None, task_id: str=None, title: str=None, content: str=None, priority: int=None, start_date: str=None, content_front: bool=False):
        """更新任务。
        
        Args:
            project_id: 项目ID
            task_id: 任务ID
        """
        task_get_resp = self.task_get(project_id, task_id)
        if task_get_resp.code == 0:
            exists_content = task_get_resp.data['content']
            
            if content_front:
                content = f'{content}\n{exists_content}'
            else:
                content = f'{exists_content}\n{content}'
                
        elif task_get_resp.code == 1:
            return task_get_resp
        
        payload = {
            "projectId": project_id,
            "taskId": task_id,
            "title": title,
            "content": content,
            "priority": priority,
        }
        if start_date:
            payload["startDate"] = start_date
            
        return self.request(api_url=f"/open/v1/task/{task_id}", method="POST", payload=payload)

    def get_projects(self) -> ReturnResponse:
        response = requests.request(
            method='GET',
            url=f'{self.base_url}/open/v1/project',
            headers=self.headers,
            timeout=self.timeout
        )
        if response.status_code == 200:
            return ReturnResponse(code=0, msg=f"获取到 {len(response.json())} 条 project", data=response.json())
        else:
            return ReturnResponse(code=1, msg=f"获取 project 失败: {response.status_code}", data=response.json())
    
if __name__ == "__main__":
    pass