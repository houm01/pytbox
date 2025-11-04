#!/usr/bin/env python3

import re
from typing import Literal, Optional, List

from requests.auth import HTTPBasicAuth
import requests

from .utils.response import ReturnResponse


class PyJira:
    """JIRA API客户端类
    
    提供JIRA操作的封装方法，支持任务创建、更新、查询等功能。
    建议使用OAuth 2.0认证以提高安全性。
    """
    
    def __init__(self, 
                 base_url: str=None,
                 proxies: dict=None,
                 token: str=None,
                 username: str=None,
                 password: str=None,
                 timeout: int=10
            ) -> None:
        '''
        _summary_

        Args:
            base_url (str, optional): _description_. Defaults to None.
            proxies (dict, optional): _description_. Defaults to None.
            token (str, optional): _description_. Defaults to None.
            username (str, optional): _description_. Defaults to None.
            password (str, optional): _description_. Defaults to None.
        '''
        self.base_url = base_url
        self.rest_version = 3
        self.proxies = None

        if 'atlassian.net' in self.base_url:
            self.deploy_type = 'cloud'
            self.rest_version = 3
        else:
            self.deploy_type = 'datacenter'
            self.rest_version = 2

        if self.deploy_type == 'cloud':
            self.headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Basic {token}"
            }
        else:
            self.headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
            self.auth = HTTPBasicAuth(username, password)
        
        self.timeout = timeout
        # 使用 requests.Session 统一管理连接与 headers（不改变现有硬编码与参数传递逻辑）
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def get_project_boards(self, project_key: Literal['TEST'] = 'TEST') -> list:
        """获取指定项目的看板列表
        
        Args:
            project_key: 项目key，例如 'OPS'
            
        Returns:
            list: 看板列表
        """
        boards = self.jira.boards(projectKeyOrID=project_key)
        for board in boards:
            print(board.name)
        return boards

    def issue_get(self, issue_id_or_key: str, account_id: bool = False) -> ReturnResponse:
        """获取指定JIRA任务
        
        Args:
            issue_key: 任务key，例如 'TEST-50'
            account_id: 是否返回账户ID，默认为False
            
        Returns:
            dict: 任务信息或账户ID
        """
        url = f"{self.base_url}/rest/api/{self.rest_version}/issue/{issue_id_or_key}"
        print(url)
        r = self.session.get(url, headers=self.headers, timeout=self.timeout)
        
        print(r.text)
        
        # 移除所有 key 以 customfield_ 开头且后面跟数字的字段
        fields = r.json()['fields']
        keys_to_remove = [k for k in fields if k.startswith('customfield_') and k[12:].isdigit()]
        for k in keys_to_remove:
            fields.pop(k)
        
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f'获取 issue [{issue_id_or_key}] 成功', data=fields)
        else:
            return ReturnResponse(code=1, msg=f'获取 issue [{issue_id_or_key}] 失败')

    def issue_get_by_key(self, issue_id_or_key:str='', get_key: Literal['assignee', 'summary', 'description', 'status']=None):
        '''
        _summary_

        Args:
            issue_id_or_key (str, optional): _description_. Defaults to ''.
            get_key: status 就是 transitions

        Raises:
            ValueError: _description_

        Returns:
            _type_: _description_
        '''
        r = self.issue_get(issue_id_or_key=issue_id_or_key)
        if r.code == 0:
            if get_key:
                # print(get_key)
                # print(r.data['assignee'])
                try:
                    return r.data[get_key]
                except KeyError as e:
                    return r.data
        else:
            raise ValueError(f"{issue_id_or_key} 的 {get_key} 未查找到")
            

    def issue_create(self, 
                    project_id: int = 10000, 
                    summary: Optional[str] = None, 
                    description: str = None, 
                    description_adf: bool=True,
                    issue_type: Literal['任务'] = '任务', 
                    priority: Literal['Highest', 'High', 'Medium', 'Low', 'Lowest'] = 'Medium',
                    reporter: dict=None,
                    assignee: dict={},
                    parent_key: Optional[str] = None) -> ReturnResponse:
        """创建一个新的JIRA任务
        
        Args:
            project_id: 项目ID，默认为 10000
            summary: 任务标题
            description: 任务描述，默认为空字符串，支持普通文本，会自动转换为ADF格式
            issue_type: 任务类型，默认为 'Task'
            priority: 优先级，默认为 'Medium'
            parent_key: 父任务key，如果提供则创建子任务，默认为None
            reporter(dict): { "name": reporter}, : {"id" : xx}
            assignee: {"accountId": "xxx"}
            
        Returns:
            Response: 创建结果，包含任务信息或错误信息
        """
        url = f"{self.base_url}/rest/api/{self.rest_version}/issue"
        data = {
            "fields": {
                'project': { "id": project_id},
                'summary': summary,
                'issuetype': { "name": issue_type},
                'priority': { "name": priority},
                # 'reporter': reporter
            }
        }
        if assignee:
            data['fields']['assignee'] = assignee
        if description:
            # 将普通文本转换为ADF格式
            if description_adf:
                data['fields']['description'] = self.text_to_adf(description)
            else:
                data['fields']['description'] = description
            
        if parent_key:
            data['fields']['parent'] = {"key": parent_key}
    
        if reporter:
            if isinstance(reporter, str):
                data['fields']['reporter'] = {"name": reporter}
            else:
                data['fields']['reporter'] = reporter

        r = self.session.post(
            url,
            headers=self.headers,
            json=data,
            timeout=self.timeout,
            proxies=self.proxies
        )
        if r.status_code == 201:
            return ReturnResponse(code=0, msg=f'创建 issue [{summary}] 成功', data=r.json())
        else:
            return ReturnResponse(code=1, msg=f'创建 issue [{summary}] 失败, {r.text}')
        

    def issue_update(self, 
                     issue_key: str, 
                     summary: Optional[str] = None, 
                     description: str = None, 
                     issue_type: str = None,
                     priority: Literal['Blocker', 'Critical', 'Major', 'Minor'] = None,
                     labels: Optional[list[str]] = None,
                     parent_key: str=None) -> dict:
        """更新JIRA任务
        
        Args:
            issue_key: 任务key，例如 'TEST-50'
            summary: 任务标题，默认为None
            description: 任务描述，默认为空字符串，支持普通文本，会自动转换为ADF格式
            issue_type: 任务类型，默认为 'Task'
            priority: 优先级，默认为 'Minor'
            assignee: 分配人，默认为 'MingMing Hou'
            status: 任务状态，默认为None
            labels: 标签列表，默认为None
            
        Returns:
            dict: 更新后的任务信息或错误信息
        """
        url = f"{self.base_url}/rest/api/{self.rest_version}/issue/{issue_key}"
        data = { "fields": {} }
        if summary:
            data['fields']['summary'] = summary
        if description is not None:
            description = self.format_description(description)
            # 将普通文本转换为ADF格式
            data['fields']['description'] = self.text_to_adf(description)
        if issue_type:
            data['fields']['issuetype'] = issue_type
        if priority:
            data['fields']['priority'] = {"name": priority}
        if labels:
            data['fields']['labels'] = labels
            
        if parent_key:
            data['fields']['parent'] = {"key": parent_key}
        
        # print(data)
        r = self.session.put(url, headers=self.headers, json=data, timeout=self.timeout)
        if r.status_code == 204:
            return ReturnResponse(code=0, msg=f'更新 issue [{issue_key}] 成功', data=r.text)
        else:
            try:
                error_data = r.json()
                error_message = f'更新 issue [{issue_key}] 失败, status: {r.status_code}, 错误: {error_data}'
            except:
                error_message = f'更新 issue [{issue_key}] 失败, status: {r.status_code}, 响应: {r.text}'
            return ReturnResponse(code=1, msg=error_message, data=r.text)

    def issue_assign(self, issue_id_or_key: str='', name: str=None, display_name: str=None, account_id: str=None) -> ReturnResponse:
        '''
        _summary_

        Args:
            issue_id_or_key (str, optional): _description_. Defaults to ''.
            name (str, optional): _description_. Defaults to None.
            display_name (str, optional): _description_. Defaults to None.
            account_id (str, optional): _description_. 侯明明: 612dbc1d1dbcd90069240013 包柿林: 712020:66dfa4a9-383e-4aa2-abdd-521adfccf967

        Returns:
            ReturnResponse: _description_
        '''    
        update = False
        url = f"{self.base_url}/rest/api/{self.rest_version}/issue/{issue_id_or_key}/assignee"
        data = {}
        if name:
            data["name"] = name
            assignee_message = name
            update = True
            
        if display_name:
            data["displayName"] = display_name
            assignee_message = display_name
            update = True
            
        if account_id:
            account_info = self.issue_get_by_key(issue_id_or_key=issue_id_or_key, get_key='assignee')
            if account_info is None:
                update = True
            else:
                current_account_id = account_info['accountId']
                if current_account_id != account_id:
                    update = True
            
            data["accountId"] = account_id
            assignee_message = account_id

        if update:
            r = self.session.put(url, headers=self.headers, json=data, timeout=self.timeout)
            if r.status_code == 204:
                return ReturnResponse(code=0, msg=f'更新 issue [{issue_id_or_key}] 的分配人成功, 经办人被更新为 {assignee_message}', data=r.text)
            return ReturnResponse(code=1, msg=f'更新 issue [{issue_id_or_key}] 的分配人失败, status code: {r.status_code}, 报错: {r.text}')
        return ReturnResponse(code=0, msg=f'issue [{issue_id_or_key}] 的分配人已经为 {assignee_message}, 不需要更新')

    def issue_comment_add(self, issue_key: str, comment: str) -> dict:
        """添加JIRA任务评论
        
        Args:
            issue_key: 任务key，例如 'TEST-50'
            comment: 评论内容
            
        Returns:
            dict: 评论信息
        """
        url = f"{self.base_url}/rest/api/{self.rest_version}/issue/{issue_key}/comment/"
        comment_adf = self.text_to_adf(text=self.format_description(comment))
        r = self.session.post(url, headers=self.headers, json={"body": comment_adf}, timeout=self.timeout)
        if r.status_code == 201:
            return ReturnResponse(code=0, msg=f'添加评论 [{comment}] 成功', data=r.json())
        else:
            return ReturnResponse(code=1, msg=f'添加评论 [{comment}] 失败, 返回值: {r.text}', data=r.json())
    
    def issue_search(self, jql: str, max_results: int = 1000, fields: Optional[List[str]] = None) -> ReturnResponse:
        """使用JQL搜索JIRA任务（支持自动分页获取所有结果）
        https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-search/#api-rest-api-3-search-jql-get
        
        Args:
            jql: JQL查询字符串
            max_results: 最大返回结果数，默认1000。会自动分页获取
            fields: 需要返回的字段列表，默认返回所有字段
            
        Returns:
            ReturnResponse: 包含任务列表的响应数据
        """
        url = f"{self.base_url}/rest/api/3/search/jql"
        
        # Jira API 单次请求最多返回100条，需要分页
        page_size = 100
        all_issues = []
        seen_keys = set()  # 用于去重
        next_page_token = None
        page_count = 0
        
        while len(all_issues) < max_results:
            page_count += 1
            
            # 构建查询参数
            params = {
                "jql": jql,
                "maxResults": page_size
            }
            
            # 如果有下一页的 token，添加到参数中（按文档使用 nextPageToken 参数名）
            if next_page_token:
                params["nextPageToken"] = next_page_token
            
            # 如果指定了字段，添加到查询参数中
            if isinstance(fields, list):
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = fields
            
            r = self.session.get(url, headers=self.headers, params=params, timeout=self.timeout)
            
            if r.status_code != 200:
                return ReturnResponse(code=1, msg=f'获取 issue 失败, status code: {r.status_code}, 报错: {r.text}')
            
            data = r.json()
            issues = data.get('issues', [])
            
            if not issues:
                break
            
            # 去重：只添加未见过的 issue
            new_issues_count = 0
            for issue in issues:
                issue_key = issue.get('key')
                if issue_key and issue_key not in seen_keys:
                    all_issues.append(issue)
                    seen_keys.add(issue_key)
                    new_issues_count += 1
                
            # 检查是否是最后一页
            is_last = data.get('isLast', True)
            next_page_token = data.get('nextPageToken')
            
            # 如果是最后一页或没有新数据，退出循环
            if is_last or new_issues_count == 0:
                break
        
        # 如果获取的数据超过 max_results，截断到指定数量
        if len(all_issues) > max_results:
            all_issues = all_issues[:max_results]
        
        # 返回合并后的结果
        result_data = {
            'issues': all_issues,
            'total': len(all_issues),
            'startAt': 0
        }
        
        return ReturnResponse(code=0, msg=f'成功获取 {len(all_issues)} 个唯一 issue（共请求 {page_count} 页）', data=result_data)


    def get_boards(self) -> ReturnResponse:
        """获取所有看板信息并打印
        
        使用REST API获取看板信息，主要用于调试和查看。
        """
        url = f"{self.base_url}/rest/agile/1.0/board"
        response = self.session.get(url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return ReturnResponse(code=0, msg='', data=response.json())
 
    def get_issue_fields(self) -> ReturnResponse:
        url = f"{self.base_url}/rest/api/3/field"
        response = self.session.get(url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return ReturnResponse(code=0, msg='', data=response.json())
 
    def get_project(self, project_id_or_key: Literal['TEST']='TEST') -> ReturnResponse:
        if self.deploy_type == 'cloud':
            url = f"{self.base_url}/rest/api/3/project/{project_id_or_key}"
        else:
            url = f"{self.base_url}/rest/api/2/project"
            
        response = self.session.get(url, headers=self.headers, timeout=self.timeout)
        if response.status_code == 401:
            return ReturnResponse(code=1, msg=response.text)
        else:
            return ReturnResponse(code=0, msg='', data=response.json())

    # def get_issue(self, issue_id_or_key: str) -> ReturnResponse:
    #     url = f"{self.base_url}/rest/api/{self.rest_version}/issue/{issue_id_or_key}"
    #     response = self.session.get(url, headers=self.headers, timeout=self.timeout)
    #     if response.status_code == 200:
    #         return ReturnResponse(code=0, msg=f'根据输入的 {issue_id_or_key} 成功获取到 issue', data=response.json())
    #     else:
    #         return ReturnResponse(code=1, msg=response.text)
 
    def get_metadata_for_project_issue_types(self, project_id_or_key: Literal['TEST', 'MO', '10000']='TEST'):
        url = f"{self.base_url}/rest/api/2/issue/createmeta/{project_id_or_key}/issuetypes"
        response = self.session.get(url, headers=self.headers, timeout=self.timeout)
        if response.status_code == 200:
            return ReturnResponse(code=0, msg='', data=response.json())
        else:
            return ReturnResponse(code=1, msg=f"{response.status_code}: {response.text}")
 
    def get_metadata_for_issue_type_used_for_create_issue(self, project_id_or_key: Literal['TEST', 'MO']='TEST', issue_type_id: Literal['10000']='10000'):
        url = f"{self.base_url}/rest/api/{self.rest_version}/issue/createmeta/{project_id_or_key}/issuetypes/{issue_type_id}"
        r = self.session.get(url, headers=self.headers, timeout=self.timeout)
        return r
    
    def get_user(self, username: str=None, key: str=None):
        url = f"{self.base_url}/rest/api/{self.rest_version}/user"
        r = self.session.get(url, headers=self.headers, params={'username': username}, timeout=self.timeout)
        return r
    
    def get_issue_property(self, issue_id_or_key):
        url = f"{self.base_url}/rest/api/2/issue/{issue_id_or_key}/properties"
        r = self.session.get(url, headers=self.headers, timeout=self.timeout)
        return r
    
    def find_user(self, query: str) -> ReturnResponse:
        '''
        查找用户

        Args:
            query (str): 建议输入用户的邮箱

        Returns:
            _type_: 
        '''
        url = f"{self.base_url}/rest/api/{self.rest_version}/user/search"
        r = self.session.get(url, headers=self.headers, params={'query': query}, timeout=self.timeout)
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f'查找到 {len(r.json())} 个用户', data=r.json()[0])
        else:
            return ReturnResponse(code=1, msg=f'获取用户失败, status code: {r.status_code}, 报错: {r.text}')
    
    def get_issue_transitions(self, issue_id_or_key) -> ReturnResponse:
        url = f"{self.base_url}/rest/api/{self.rest_version}/issue/{issue_id_or_key}/transitions"
        r = self.session.get(url, headers=self.headers, timeout=self.timeout)
        if r.status_code == 200:
            return ReturnResponse(code=0, msg='', data=r.json())
        else:
            return ReturnResponse(code=1, msg=f'获取 issue [{issue_id_or_key}] 的 transitions 失败, status code: {r.status_code}, 报错: {r.text}')
  
    def get_issue_transitions_by_name(self, issue_id_or_key, name) -> ReturnResponse:
        r = self.get_issue_transitions(issue_id_or_key=issue_id_or_key)
        for transition in r.data['transitions']:
            if transition['name'] == name:
                return ReturnResponse(code=0, msg=f'获取 issue [{issue_id_or_key}] 的 transitions 成功, 返回值: {transition["id"]}', data=transition['id'])
        raise ValueError(f'获取 issue [{issue_id_or_key}] 的 transitions 失败, 没有找到状态为 {name} 的 transition')

    def issue_transition(self, issue_id_or_key, transition_name) -> ReturnResponse:
        update = False
        status = self.issue_get_by_key(issue_id_or_key=issue_id_or_key, get_key='status')
        if status:
            if transition_name != status['name']:
                update = True
        if update:
            url = f"{self.base_url}/rest/api/{self.rest_version}/issue/{issue_id_or_key}/transitions"
            data = {
                "transition": {
                    "id": self.get_issue_transitions_by_name(issue_id_or_key=issue_id_or_key, name=transition_name).data
                }
            }
            r = self.session.post(url, headers=self.headers, json=data, timeout=self.timeout)
            if r.status_code == 204:
                return ReturnResponse(code=0, msg=f'更新 issue [{issue_id_or_key}] 的状态成功, 状态被更新为 {transition_name}', data=r.text)
            else:
                return ReturnResponse(code=1, msg=f'更新 issue [{issue_id_or_key}] 的状态失败, status code: {r.status_code}, 报错: {r.text}')
        else:
            return ReturnResponse(code=0, msg=f'issue [{issue_id_or_key}] 的状态已经为 {status["name"]}, 不需要更新')

    def format_description(self, description):
        '''
        格式化描述
        '''
        if not description:
            return ""
        
        new_description = description
        
        # 内容清理正则表达式
        CONTENT_CLEANUP_PATTERNS = [
            r'\*\*工作历时\*\*: \d+小时',
            r'\*\*工作历时\*\*:.*小时',
            r'!\[image\]\(.*?\)',
            r'!\[file\]\(.*?\)',
            r'\[Jira Link\]\(.*?\)',
            r'bear://x-callback-url/open-note\?id=.*'
        ] 

        for pattern in CONTENT_CLEANUP_PATTERNS:
            new_description = re.sub(pattern, '', new_description)
        return new_description.strip()

    def text_to_adf(self, text: str) -> dict:
        """
        将普通文本转换为Atlassian Document Format (ADF)格式。
        
        Args:
            text: 要转换的文本内容
            
        Returns:
            dict: ADF格式的文档对象
        """
        if not text:
            return {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": ""
                            }
                        ]
                    }
                ]
            }
        
        # 将文本按行分割
        lines = text.split('\n')
        content = []
        
        for line in lines:
            if line.strip():  # 非空行
                paragraph_content = [
                    {
                        "type": "text",
                        "text": line
                    }
                ]
                content.append({
                    "type": "paragraph",
                    "content": paragraph_content
                })
            else:  # 空行，添加换行符
                if content:  # 如果前面有内容，添加换行
                    content.append({
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": ""
                            }
                        ]
                    })
        
        # 如果没有内容，至少添加一个空段落
        if not content:
            content = [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": ""
                        }
                    ]
                }
            ]
        
        return {
            "type": "doc",
            "version": 1,
            "content": content
        }

 
if __name__ == '__main__':
    pass
    