#!/usr/bin/env python3

import os
import json
import uuid
import time
import requests
import shelve
from typing import TYPE_CHECKING, Literal, Any

if TYPE_CHECKING:
    from .client import BaseClient, FeishuResponse
from .helpers import pick
from requests_toolbelt import MultipartEncoder
from ..utils.response import ReturnResponse

class Endpoint:

    def __init__(self, parent: "BaseClient") -> None:
        self.parent = parent


class AuthEndpoint(Endpoint):

    token_path = '/tmp/.feishu_token'

    def save_token_to_file(self):
        with shelve.open(self.token_path) as db:
            db['token'] = self.refresh_access_token()
            return True
    
    def fetch_token_from_file(self):
        with shelve.open(self.token_path) as db:
            token = db.get('token')
            return token

    def get_tenant_access_token(self):
        '''
        _summary_

        Returns:
            _type_: _description_
        '''
        if os.environ.get('TENANT_ACCESS_TOKEN'):
            return os.environ.get('TENANT_ACCESS_TOKEN')
        else:
            print('未找到token， 开始刷新')
            resp = self.refresh_access_token()
            if resp.tenant_access_token:
                os.environ['TENANT_ACCESS_TOKEN'] = resp.tenant_access_token
                return os.environ.get('TENANT_ACCESS_TOKEN')

    def refresh_access_token(self):
        payload = dict(
            app_id=self.parent.app_id,
            app_secret=self.parent.app_secret
        )

        token = requests.request(method='POST', 
                                    url=self.parent.options.base_url+'/auth/v3/tenant_access_token/internal', 
                                    json=payload, timeout=5).json()['tenant_access_token']
        
        os.environ['TENANT_ACCESS_TOKEN'] = token
        return token

class MessageEndpoint(Endpoint):

    def send_text(self,
                  text: str,
                  receive_id: str):
        

        format_message_content = json.dumps({ "text": text }, ensure_ascii=False)

        payload = {
                "content": format_message_content,
                "msg_type": "text",
                "receive_id": receive_id,
                "uuid": str(uuid.uuid4())
        }
        receive_id_type = self.parent.extensions.parse_receive_id_type(receive_id=receive_id)

        return self.parent.request(path=f'/im/v1/messages?receive_id_type={receive_id_type}', 
                                   method='POST',
                                   body=payload)
    
    def send_post(self,
                  receive_id: str=None,
                  message_id: str=None,
                  title: str=None,
                  content: list=None):
        '''
        发送富文本消息

        Args:
            reveive_id (str): 必选参数, 接收消息的 id, 可以是 chat_id, 也可以是 openid, 代码会自动判断
            message_id (str): 如果设置此参数, 表示会在原消息上回复消息
            title: (str): 消息的标题
            content: (list): 消息的内容, 示例格式如下
                content = [
                    [
                        {"tag": "text", "text": "VPN: XXX:8443"}
                    ]
                ]

        Returns:
            response (dict): 返回发送消息后的响应, 是一个大的 json, 还在考虑是否拆分一下
        '''
        
        message_content = {
            "zh_cn": {
                "title": title,
                "content": content
                }
            }

        format_message_content = json.dumps(message_content, ensure_ascii=False)
        
        if receive_id:
            receive_id_type = self.parent.extensions.parse_receive_id_type(receive_id=receive_id)
            api = f'/im/v1/messages?receive_id_type={receive_id_type}'
            payload = {
                "content": format_message_content,
                "msg_type": "post",
                "receive_id": receive_id,
                "uuid": str(uuid.uuid4())
            }
            
        elif message_id:
            api = f'/im/v1/messages/{message_id}/reply'
            payload = {
                "content": format_message_content,
                "msg_type": "post",
                "uuid": str(uuid.uuid4())
            }

        return self.parent.request(path=f'/im/v1/messages?receive_id_type={receive_id_type}', 
                                method='POST',
                                body=payload)

    def send_card(self, template_id: str, template_variable: dict=None, receive_id: str=None):
        '''
        目前主要使用的发送卡片消息的函数, 从名字可以看出, 这是第2代的发送消息卡片函数

        Args:
            template_id (str): 消息卡片的 id, 可以在飞书的消息卡片搭建工具中获得该 id
            template_variable (dict): 消息卡片中的变量
            receive_id: (str): 接收消息的 id, 可以填写 open_id、chat_id, 函数会自动检测

        Returns:
            response (dict): 返回发送消息后的响应, 是一个大的 json, 还在考虑是否拆分一下
        '''
        receive_id_type = self.parent.extensions.parse_receive_id_type(receive_id=receive_id)
        content = {
            "type":"template",
            "data":{
                "template_id": template_id,
                "template_variable": template_variable
            }
        }

        content = json.dumps(content, ensure_ascii=False)
        
        payload = {
           	"content": content,
            "msg_type": "interactive",
            "receive_id": receive_id
        }
        return self.parent.request(path=f'/im/v1/messages?receive_id_type={receive_id_type}', 
                                   method='POST',
                                   body=payload)

    def send_file(self, file_name, file_path, receive_id):
        receive_id_type = self.parent.extensions.parse_receive_id_type(receive_id=receive_id)
        content = {
            "file_key": self.parent.extensions.upload_file(file_name=file_name, file_path=file_path)
        }
        content = json.dumps(content, ensure_ascii=False)
        payload = {
            "content": content,
            "msg_type": "file",
            "receive_id": receive_id
        }

        return self.parent.request(path=f'/im/v1/messages?receive_id_type={receive_id_type}', 
                            method='POST',
                            body=payload)

    def get_history(self, chat_id: str=None, chat_type: Literal['chat', 'thread']='chat', start_time: int=int(time.time())-300, end_time: int=int(time.time()), last_minute: int=5, page_size: int=50):
        '''
        _summary_

        Args:
            chat_id (str, optional): _description_. Defaults to None.
            chat_type (Literal[&#39;chat&#39;, &#39;thread&#39;], optional): _description_. Defaults to 'chat'.
            start_time (int, optional): _description_. Defaults to int(time.time())-300.
            end_time (int, optional): _description_. Defaults to int(time.time()).
            page_size (int, optional): _description_. Defaults to 50.

        Returns:
            _type_: _description_
        '''
        start_time = int(time.time()) - last_minute * 60
        return self.parent.request(path=f'/im/v1/messages?container_id={chat_id}&container_id_type={chat_type}&end_time={end_time}&page_size={page_size}&sort_type=ByCreateTimeAsc&start_time={start_time}', 
                            method='GET')
    
    def reply(self, message_id, content):
        content = {
            "text": content
        }
        payload = {
            "content": json.dumps(content, ensure_ascii=False),
            "msg_type": "text",
            "reply_in_thread": False,
        	"uuid": str(uuid.uuid4())
        }
        return self.parent.request(
            path=f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply",
            method='POST',
            body=payload
        )
    
    def forward(self, message_id, receive_id):
        receive_id_type = self.parent.extensions.parse_receive_id_type(receive_id=receive_id)
        payload = {
            "receive_id": receive_id
        }
        return self.parent.request(
            path=f"/im/v1/messages/{message_id}/forward?receive_id_type={receive_id_type}",
            method='POST',
            body=payload
        )
    
    def emoji(self, message_id, emoji_type: Literal['DONE', 'ERROR', 'SPITBLOOD', 'LIKE', 'LOVE', 'CARE', 'WOW', 'SAD', 'ANGRY', 'SILENT']) -> ReturnResponse:
        '''
        表情文案说明: https://open.feishu.cn/document/server-docs/im-v1/message-reaction/emojis-introduce

        Args:
            message_id (_type_): _description_
            emoji_type (str): _description_

        Returns:
            _type_: _description_
        '''
        payload = {
            "reaction_type": {
                "emoji_type": emoji_type
            }
        }

        r = self.parent.request(
            path=f"im/v1/messages/{message_id}/reactions",
            method='POST',
            body=payload
        )
        if r.code == 0:
            return ReturnResponse(code=0, msg=f"{message_id} 回复 emoji [{emoji_type}] 成功")
        else:
            return ReturnResponse(code=1, msg=f"{message_id} 回复 emoji [{emoji_type}] 失败")

    def webhook_send_feishu_card(self, webhook_url: str,template_id: str=None, template_version: str='1.0.0', template_variable: dict={}) -> ReturnResponse:
        '''
        https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot
        https://open.feishu.cn/document/feishu-cards/quick-start/send-message-cards-with-custom-bot

        Args:
            template_id (str, optional): _description_. Defaults to None.
            template_version (str, optional): _description_. Defaults to '1.0.0'.
            template_variable (dict, optional): _description_. Defaults to {}.

        Returns:
            ReturnResponse: _description_
        '''

        hearders = {
            "Content-type": "application/json",
            "charset":"utf-8"
        }

        payload = {
            "msg_type": "interactive",
            "card":
                {
                    "type":"template",
                    "data":
                        {
                            "template_id": template_id,
                            "template_version_name": template_version, 
                            "template_variable": template_variable
                        }
                    }
            }
        resp = requests.request(url=webhook_url, method='POST', json=payload, headers=hearders)
        if resp.status_code == 200:
            return ReturnResponse(code=0, msg=resp.text, data=resp.json())
        else:
            return ReturnResponse(code=1, msg=resp.text, data=resp.json())


class BitableEndpoint(Endpoint):
    
    def list_records(self, app_token, table_id, field_names: list=None, automatic_fields: bool=False, filter_conditions: list=None, conjunction: Literal['and', 'or']='and', sort_field_name: str=None, view_id: str=None):
        '''
        如果是多维表格中的表格, 需要先获取 app_token
        https://open.feishu.cn/document/server-docs/docs/wiki-v2/space-node/get_node?appId=cli_a1ae749cd7f9100d
        
        参考文档: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/bitable-v1/app-table-record/search

        Args:
            app_token (_type_): obj_token 
            table_id (_type_): _description_
            filter_conditions (_type_): https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/bitable-v1/app-table-record/record-filter-guide
        '''
        payload = {
            "automatic_fields": automatic_fields,
            "field_names": field_names,
            "filter": {
                "conditions": filter_conditions,
                "conjunction": conjunction
            },
            "view_id": view_id
        }
        
        if sort_field_name:
            payload['sort'] = [
                {
                    "desc": True,
                    "field_name": sort_field_name
                }
            ]
            
        records = self.parent.request(path=f'/bitable/v1/apps/{app_token}/tables/{table_id}/records/search', method='POST', body=payload)
        if records.code == 0:
            new_dict = {}
            for item in records.data['items']:
                for key, value in item['fields'].items():
                    if isinstance(value, list):
                        try:
                            value = value[0].get('text')
                        except AttributeError:
                            pass
                    new_dict[key] = value
                yield new_dict
        elif records.code != 0:
            pass
    
    def add_record(self, app_token, table_id, fields):
        payload = {
            "fields": fields
        }
        return self.parent.request(path=f'/bitable/v1/apps/{app_token}/tables/{table_id}/records',
                                   method='POST',
                                   body=payload)

    def query_record(self, app_token: str=None, table_id: str=None, automatic_fields: bool=False, field_names: list=None, filter_conditions: list=None, conjunction: Literal['and', 'or']='and', sort_field_name: str=None, view_id: str=None):
        '''
        https://open.feishu.cn/api-explorer/cli_a1ae749cd7f9100d?apiName=search&from=op_doc_tab&project=bitable&resource=app.table.record&version=v1
        Args:
            app_token (_type_): _description_
            table_id (_type_): _description_
            view_id (_type_): _description_
            automatic_fields (_type_): _description_
            field_names (_type_): _description_
            filter_conditions (_type_): [
                        {
                            "field_name": "职位",
                            "operator": "is",
                            "value": [
                                "初级销售员"
                            ]
                        },
                        {
                            "field_name": "销售额",
                            "operator": "isGreater",
                            "value": [
                                "10000.0"
                            ]
                        }
                    ],
            conjunction (_type_): _description_
            sort_field_name (_type_): _description_
            view_id (_type_): _description_

        Returns:
            _type_: _description_
        '''
        payload = {
            "automatic_fields": automatic_fields,
            "field_names": field_names,
            "filter": {
                    "conditions": filter_conditions,
                    "conjunction": conjunction
                },
            "view_id": view_id
        }
        if sort_field_name:
            payload['sort'] = [
                {
                    "desc": True,
                    "field_name": sort_field_name
                }
            ]
        return self.parent.request(path=f'/bitable/v1/apps/{app_token}/tables/{table_id}/records/search',
                                   method='POST',
                                   body=payload)

    def query_record_id(self, 
                        app_token: str=None, 
                        table_id: str=None, filter_field_name: str=None, filter_value: str=None) -> str | None:
        '''
        用于单向或双向关联

        Args:
            app_token (str, optional): _description_. Defaults to None.
            table_id (str, optional): _description_. Defaults to None.
            filter_field_name (str, optional): _description_. Defaults to None.
            filter_value (str, optional): _description_. Defaults to None.

        Returns:
            str | None: _description_
        '''
        payload = {
            "automatic_fields": False,
            "filter": {
                    "conditions": [
                        {
                            "field_name": filter_field_name,
                            "operator": "is",
                            "value": [filter_value]
                        }
                ],
                    "conjunction": "and"
                },
            }
        res = self.parent.request(path=f'/bitable/v1/apps/{app_token}/tables/{table_id}/records/search',
                                   method='POST',
                                   body=payload)
        if res.code == 0:
            try:
                return res.data['items'][0]['record_id']
            except IndexError:
                return None
        else:
            return None
        
    def add_and_update_record(self, 
                              app_token: str=None, 
                              table_id: str=None, 
                              record_id: str=None, 
                              fields: dict=None,
                              filter_field_name: str=None,
                              filter_value: str=None) -> ReturnResponse:
        '''
        _summary_

        Args:
            app_token (_type_): _description_
            table_id (_type_): _description_
            record_id (_type_): _description_
            fields (_type_): _description_

        Returns:
            ReturnResponse: _description_
        '''
        record_id = self.query_record_id(app_token, table_id, filter_field_name, filter_value)
        
        if record_id:
            payload = {
                "fields": {k: v for k, v in fields.items() if v is not None}
            }
            resp = self.parent.request(path=f'/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}',
                                        method='PUT',
                                        body=payload)
            return ReturnResponse(code=resp.code, msg=f"记录已存在, 进行更新", data=resp.data)
        else:
            resp = self.add_record(app_token, table_id, fields)
            return ReturnResponse(code=resp.code, msg=f"记录不存在, 进行创建", data=resp.data)

    def query_name_by_record_id(self, app_token: str=None, table_id: str=None, field_names: list=None, record_id: str='', name: str=''):
        response = self.query_record(app_token=app_token, table_id=table_id, field_names=field_names)
        if response.code == 0:
            for item in response.data['items']:
                if item['record_id'] == record_id:
                    # print(item['fields'])
                    return self.parent.extensions.parse_bitable_data(item['fields'], name)
                # ss
        else:
            return None

class DocsEndpoint(Endpoint):

    def rename_doc_title(self, space_id, node_token, title):
        payload = {
            "title": title
        }
        return self.parent.request(path=f'/wiki/v2/spaces/{space_id}/nodes/{node_token}/update_title',
                                   method='POST',
                                   body=payload)

    def create_doc(self, space_id: str, parent_node_token: str, title: str):
        '''
        在知识库中创建文档

        Args:
            space_id (_type_): 知识库的 id
            parent_node_token (_type_): 父节点 token, 通过浏览器的链接可以获取, 例如 https://tyun.feishu.cn/wiki/J4tjweM5xiCBADk1zo7c6wXOnHO

        Returns:
            _type_: document.id: res.data['node']['obj_token']
        '''
        payload = {
            "node_type": "origin",
            "obj_type": "docx",
            "parent_node_token": parent_node_token
        }
        res = self.parent.request(path=f'/wiki/v2/spaces/{space_id}/nodes',
                                   method='POST',
                                   body=payload)
        if res.code == 0:
            self.rename_doc_title(space_id=space_id, node_token=res.data['node']['node_token'], title=title)
            return res
        else:
            return res

    def create_block(self, document_id: str=None, block_id: str=None, client_token: str=None, payload: dict={}):
        '''
        _summary_

        Args:
            document_id (str, optional): _description_. Defaults to None.
            block_id (str, optional): _description_. Defaults to None.
            client_token (str, optional): _description_. Defaults to None.
            children (list, optional): _description_. Defaults to None.

        Returns:
            _type_: _description_
        '''
        if payload.get('children_id'):
            # 创建嵌套块, 参考文档 
            # https://open.feishu.cn/api-explorer/cli_a1ae749cd7f9100d?apiName=create&from=op_doc_tab&project=docx&resource=document.block.descendant&version=v1
            return self.parent.request(path=f'/docx/v1/documents/{document_id}/blocks/{block_id}/descendant',
                                    method='POST',
                                    body=payload)
        elif payload.get('children')[0]['block_type'] == 27:
            
            r = self.parent.request(path=f'/docx/v1/documents/{document_id}/blocks/{block_id}/children',
                                    method='POST',
                                    body=payload)
            block_id = r.data['children'][0]['block_id']          
            
            file_token = self.parent.extensions.upload_media(
                file_path=payload['file_path'],
                block_id=block_id
            )['data']['file_token']
            
            res = self.update_block(
                document_id=document_id,
                block_id=block_id,
                replace_image_token=file_token,
                image_width=payload['image_width'],
                image_height=payload['image_height'],
                image_align=payload['image_align']
            )
            return res
            # print(payload)
        else:
            # print(payload)
            return self.parent.request(path=f'/docx/v1/documents/{document_id}/blocks/{block_id}/children',
                                    method='POST',
                                    body=payload)
    
    def create_block_children(self, document_id: str=None, block_id: str=None, payload: dict=None):
        return self.parent.request(path=f'/docx/v1/documents/{document_id}/blocks/{block_id}/children',
                                    method='POST',
                                    body=payload)

    def update_block(self, document_id: str=None, block_id: str=None, replace_image_token: str=None, image_width: int=100, image_height: int=100, image_align: int=2):
        payload = {}
        if replace_image_token:
            payload['replace_image'] = {
                'token': replace_image_token,
                'width': image_width,
                'height': image_height,
                'align': image_align
            }
        return self.parent.request(path=f'/docx/v1/documents/{document_id}/blocks/{block_id}',
                                    method='PATCH',
                                    body=payload)

class CalendarEndpoint(Endpoint):
    def get_events(self, 
                   calendar_id: str='feishu.cn_dQ4cLmSfGa1QSWqv3EvpLf@group.calendar.feishu.cn', 
                   start_time: int=int(time.time()) - 30*24*60*60, 
                   end_time: int=int(time.time()), 
                   page_size: int=500,
                   anchor_time: int=None
                ):
        if anchor_time:
            anchor_time = f'&anchor_time={anchor_time}'
        else:
            anchor_time = ''
        return self.parent.request(path=f'/calendar/v4/calendars/{calendar_id}/events?anchor_time={start_time}&end_time={end_time}&page_size={page_size}&start_time={start_time}',
                                   method='GET')


class ExtensionsEndpoint(Endpoint):
    def parse_receive_id_type(self, receive_id):
        if receive_id.startswith('ou'):
            receive_id_type = 'open_id'
        elif receive_id.startswith('oc'):
            receive_id_type = 'chat_id'
        else:
            raise ValueError('No such named receive_id')
        return receive_id_type

    def upload_file(self, file_name, file_path):

        files = {
            'file_type': ('', 'stream'),
            'file_name': ('', file_name),
            'file': open(file_path, 'rb')
        }

        return self.parent.request(path='/im/v1/files',
                                   method='POST',
                                   files=files).data['file_key']

    def upload_image(self, image_path):
        import requests
        from requests_toolbelt import MultipartEncoder
        
        url = "https://open.feishu.cn/open-apis/im/v1/images"
            
        form = {
                'image_type': 'message',
                'image': (open(image_path, 'rb'))
            }  # 需要替换具体的path 
        
        multi_form = MultipartEncoder(form)
        if self.parent.auth.fetch_token_from_file():
            token = self.parent.auth.fetch_token_from_file()
        else:
            self.parent.auth.save_token_to_file()
            token = self.parent.auth.fetch_token_from_file()
        headers = {
            'Authorization': f'Bearer {token}',  ## 获取tenant_access_token, 需要替换为实际的token
        }
        headers['Content-Type'] = multi_form.content_type
        response = requests.request("POST", url, headers=headers, data=multi_form)
        response_json = response.json()
        if response_json['code'] == 0:
            return response_json['data']['image_key']
    
    
    def build_block_heading(self, content, heading_level: Literal[1, 2, 3, 4]):
        return {
            "index": 0,
            "children": [
                {
                    "block_type": heading_level + 2,
                    f"heading{heading_level}": {
                        "elements": [
                            {
                                "text_run": {
                            "content": content
                        }
                    }
                ]
            },
                    "style": {}
                }
            ]
        }
    
    def build_block_element(self, content: str=None, background_color: int=None, text_color: int=None):
        element = {
                "text_run": {
                    "content": content,
                    "text_element_style": {}
                }
            }
        
        if background_color:
            element['text_run']['text_element_style']['background_color'] = background_color
        
        if text_color:
            element['text_run']['text_element_style']['text_color'] = text_color

        return element

    def build_block_text(self, elements: list=None) -> dict:
        '''
        构建飞书文档文本块。
        https://open.feishu.cn/document/docs/docs/data-structure/block

        Args:
            elements (list, optional): 请使用 build_block_element 函数构建元素

        Returns:
            dict: 飞书文档文本块
        '''
        return {
            "index": 0,
            "children": [
                {
                    "block_type": 2,
                    "text": {
                        "elements": elements,
                        "style": {}
                    }
                }
            ]
        }
    
    def build_block_bullet(self, content_list: list = None, background_color: int=None, text_color: int=None) -> dict:
        """
        构建飞书文档项目符号列表块。

        Args:
            content_list (list, optional): 内容列表，将批量添加到 children 中

        Returns:
            dict: 飞书文档项目符号列表块
        """
        children = []
        
        for content in content_list:
            children.append({
                "block_type": 12,
                "bullet": {
                    "elements": [
                        self.build_block_element(content=content, background_color=background_color, text_color=text_color)
                    ]
                }
            })
            
        return {
            "index": 0,
            "children": children
        }

    def build_block_ordered_list(self, content_list: list = None, background_color: int=None, text_color: int=None) -> dict:
        """
        构建飞书文档项目符号列表块。

        Args:
            content_list (list, optional): 内容列表，将批量添加到 children 中

        Returns:
            dict: 飞书文档项目符号列表块
        """
        children = []
        
        for content in content_list:
            children.append({
                "block_type": 13,
                "ordered": {
                    "elements": [
                        self.build_block_element(content=content, background_color=background_color, text_color=text_color)
                    ]
                }
            })
            
        return {
            "index": 0,
            "children": children
        }
    
    def build_block_callout(self, content: str=None, background_color: int=1, border_color: int=2, text_color: int=5, emoji_id: str='grinning', bold: bool=False):
        '''
        _summary_

        Args:
            content (str, optional): _description_. Defaults to None.
            background_color (int, optional): _description_. Defaults to 1.
            border_color (int, optional): _description_. Defaults to 2.
            text_color (int, optional): _description_. Defaults to 5.
            emoji_id (str, optional): _description_. Defaults to 'grinning'.
            bold (bool, optional): _description_. Defaults to False.

        Returns:
            _type_: _description_
        '''
        return {
            "index": 0,
            "children_id": [
                "callout1",
            ],
            "descendants": [
                {
                    "block_id": "callout1",
                    "block_type": 19,
                    "callout": {
                        "background_color": background_color,
                        "border_color": border_color,
                        "text_color": text_color,
                        "emoji_id": emoji_id
                    },
                    "children": [
                        "text1",
                    ]
                },
                {
                    "block_id": "text1",
                    "block_type": 2,
                    "text": {
                        "elements": [
                            {
                                "text_run": {
                                    "content": content,
                                    "text_element_style": {
                                        "bold": bold
                                    }
                                }
                            }
                        ]
                    }
                }
            ]
        }
    
    def build_block_table(self, rows: int=1, columns: int=1, column_width: list=[], data=None):
        """
        构建飞书文档表格块
        参考文档: https://open.feishu.cn/document/docs/docs/faq
        
        Args:
            rows: 表格行数
            columns: 表格列数
            data: 表格数据，可以是二维列表[[cell1, cell2], [cell3, cell4]]
                或者单元格块ID的列表
            
        Returns:
            dict: 符合飞书文档API要求的表格结构
        """
        # 生成表格ID和单元格ID
        table_id = f"table_{uuid.uuid4().hex[:8]}"
        cell_ids = []
        cell_blocks = []
        
        # if data:
        #     # 在data列表末尾添加一条新数据
        #     data.append(['sss'] * columns)  # 添加一个空行
        
        # print(data)
        
        # 生成单元格ID和块
        for row in range(rows):
            row_cells = []
            for col in range(columns):
                cell_id = f"cell_{row}_{col}_{uuid.uuid4().hex[:4]}"
                row_cells.append(cell_id)
                
                # 获取单元格内容
                cell_content = ""
                if data and len(data) > row and isinstance(data[row], (list, tuple)) and len(data[row]) > col:
                    cell_content = data[row][col]
                
                # 创建单元格内容块ID
                content_id = f"content_{cell_id}"
                
                # 创建单元格块
                cell_block = {
                    "block_id": cell_id,
                    "block_type": 32,  # 表格单元格
                    "table_cell": {},
                    "children": [content_id]
                }
                
                # 创建单元格内容块
                content_block = {
                    "block_id": content_id,
                    "block_type": 2,  # 文本块
                    "text": {
                        "elements": [
                            {
                                "text_run": {
                                    "content": str(cell_content) if cell_content else ""
                                }
                            }
                        ],
                        "style": {
                            "bold": True,
                            "align": 2
                        }
                    },
                    "children": []
                }
                
                cell_blocks.append(cell_block)
                cell_blocks.append(content_block)
            
            cell_ids.extend(row_cells)
        
        # 创建表格主块
        table_block = {
            "block_id": table_id,
            "block_type": 31,  # 表格
            "table": {
                "property": {
                    "row_size": rows,
                    "column_size": columns,
                    "header_row": True,
                    "column_width": column_width
                }
            },
            "children": cell_ids
        }
        
        # 构建完整结构
        result = {
            "index": 0,
            "children_id": [table_id],
            "descendants": [table_block] + cell_blocks
        }
        # print(result)
        return result

    def build_bitable_text(self, text: str=None):
        return {"title": text}

    def build_block_image(self, file_path, percent: int=100, image_align: int=2):

        from PIL import Image
        with Image.open(file_path) as img:
            width, height = img.size
            image_width =  int(width * percent / 100)
            image_height = int(height * percent / 100)
            
        return {
            "index": 0,
            "children": [
                {
                    "block_type": 27,
                    "image": {}
                }
            ],
            "file_path": file_path,
            "image_width": image_width,
            "image_height": image_height,
            "image_align": image_align
        }

    def upload_media(self, file_path: str, block_id: str):
        file_size = os.path.getsize(file_path)
        url = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all"
        form = {'file_name': 'demo.jpeg',
                'parent_type': 'docx_image',
                'parent_node': block_id,
                'size': str(file_size),
                'file': (open(file_path, 'rb'))}  
        multi_form = MultipartEncoder(form)
        headers = {
            'Authorization': f'Bearer {self.parent.auth.fetch_token_from_file()}',  ## 获取tenant_access_token, 需要替换为实际的token
        }
        headers['Content-Type'] = multi_form.content_type
        response = requests.request("POST", url, headers=headers, data=multi_form)
        return response.json()
    
    def create_block(self, blocks, document_id):
            # 交换blocks中元素的顺序
        blocks.reverse()
        
        for block in blocks:
            time.sleep(1)
            try:
                if block['children'][0]['block_type'] != 27:
                    self.parent.docs.create_block(
                        document_id=document_id,
                        block_id=document_id,
                        payload=block
                    )
                        
                elif block['children'][0]['block_type'] == 27:
                    block_id = self.parent.docs.create_block(
                        document_id=document_id,
                        block_id=document_id,
                        payload=block
                    ).data['children'][0]['block_id']
                    
                    file_token = self.upload_media(
                        file_path=block['file_path'],
                        block_id=block_id
                    )['data']['file_token']
                    
                    res = self.parent.docs.update_block(
                        document_id=document_id,
                        block_id=block_id,
                        replace_image_token=file_token,
                        image_width=block['image_width'],
                        image_height=block['image_height'],
                        image_align=block['image_align']
                    )
                    return res
            except KeyError:
                res = self.parent.docs.create_block(
                    document_id=document_id,
                    block_id=document_id,
                    payload=block
                )
                return res
            except IndexError:
                print(block)
    
    def parse_bitable_data(self, fields, name):
        final_data = None
        
        if fields.get(name) != None:
            if isinstance(fields[name], list):
                if fields[name][0].get('type') == 'text':
                    final_data = fields[name][0].get('text')
                elif fields[name][0].get('type') == 'url':
                    try:
                        text_2nd = fields[name][1].get('text')
                        final_data = fields[name][0].get('text') + text_2nd
                    except IndexError:
                        final_data = fields[name][0].get('text')
                        
                elif fields[name][0].get('type') == 1:
                    final_data = fields[name][0].get('value')[0]['text']
                
            elif isinstance(fields[name], int):
                if len(str(fields[name])) >= 12 and fields[name] > 10**11:
                        final_data = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(fields[name] / 1000))
                elif len(str(fields[name])) == 10 and 10**9 < fields[name] < 10**11:
                    final_data = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(fields[name]))
                else:
                    final_data = fields[name]
            elif isinstance(fields[name], dict):
                if fields[name].get('type') == 1:
                    final_data = fields[name].get('value')[0]['text']
                elif fields[name].get('type') == 3:
                    final_data = fields[name].get('value')[0]
                elif fields[name].get('type') == 5:
                    final_data = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(fields[name]['value'][0] / 1000 ))
        else:
            final_data = '待补充'
        if isinstance(final_data, str):
            return final_data
        else:
            return fields[name]

    def get_user_info(self, email: str=None, mobile: str=None, get: Literal['open_id', 'all']='all') -> ReturnResponse:
        payload = {
            "include_resigned": True,
        }
        if email:
            payload['emails'] = [email]
            user_input = email
        
        if mobile:
            payload['mobiles'] = [mobile]
            user_input = mobile
        
        response = self.parent.request(path='/contact/v3/users/batch_get_id',
                                   method='POST',
                                   body=payload)
        if response.code == 0:
            if get == 'open_id':
                return ReturnResponse(code=0, msg=f'根据用户输入的 {user_input}, 获取用户信息成功', data=response.data['user_list'][0]['user_id'])
        else:
            return ReturnResponse(code=response.code, msg=f"获取时失败, 报错请见 data 字段", data=response.data)
    
    def format_rich_text(self, text: str, color: Literal['red', 'green', 'yellow', 'blue'], bold: bool=False):
        if bold:
            text = f"**{text}**"

        if color:
            text = f"<font color='{color}'>{text}</font>"
                    
        return text
    
    def convert_str_to_dict(self, text: str):
        return json.loads(text)
    
    def parse_message_card_elements(self, elements: list | dict) -> str:
        """
        递归解析飞书消息卡片 elements，收集所有 tag 为 'text' 的文本并拼接返回。

        此方法兼容以下结构：
        - 二维列表：例如 [[{...}, {...}]]
        - 多层嵌套：字典中包含 'elements'、'content'、'children' 等容器键
        - 忽略未知/非 text 标签，例如 'unknown'

        Args:
            elements (list | dict): 飞书消息卡片的 elements 字段，可能是列表或字典。

        Returns:
            str: 拼接后的文本内容。
        """

        texts: list[str] = []

        def walk(node: Any) -> None:
            if node is None:
                return
            if isinstance(node, dict):
                tag = node.get('tag')
                if tag == 'text' and isinstance(node.get('text'), str):
                    texts.append(node['text'])
                # 递归遍历常见的容器键
                for key in ('elements', 'content', 'children'):
                    value = node.get(key)
                    if isinstance(value, (list, tuple, dict)):
                        walk(value)
            elif isinstance(node, (list, tuple)):
                for item in node:
                    walk(item)

        walk(elements)
        return ''.join(texts)
   
    def send_message_notify(self, 
                            receive_id: str='ou_ca3fc788570865cbbf59bfff43621a78', 
                            color: Literal['red', 'green', 'blue']='red', 
                            title: str='Test',
                            sub_title: str='未填写子标题',
                            priority: str='P0',
                            content: str='Test'
                        ):
        return self.parent.message.send_card(
            template_id="AAqzcy5Qrx84H",
            template_variable={
                "color": color,
                "title": title,
                "sub_title": sub_title,
                "priority": priority,
                "content": content
            },
            receive_id=receive_id
        )
    
    def get_user_info_by_open_id(self, open_id: str, get: Literal['name', 'all']='all'):
        response = self.parent.request(path=f'/contact/v3/users/{open_id}?department_id_type=open_department_id&user_id_type=open_id',
                                   method='GET')
        if response.code == 0:
            if get == 'name':
                return response.data['user']['name']
            else:
                return response.data
        else:
            return None
    
    def send_alert_notify(self,
                          event_content: str=None,
                          event_name: str=None,
                          entity_name: str=None,
                          event_time: str=None,
                          resolved_time: str=None,
                          event_description: str=None,
                          actions: str=None,
                          history: str=None,
                          color: Literal['red', 'green', 'blue']='red',
                          priority: Literal['P0', 'P1', 'P2', 'P3', 'P4']='P2',
                          receive_id: str=None
                        )
        return self.parent.message.send_card(
            template_id="AAqXPIkIOW0g9",
            template_variable={
                "color": color,
                "event_content": event_content,
                "event_name": event_name,
                "entity_name": entity_name,
                "event_time": event_time,
                "resolved_time": resolved_time,
                "event_description": event_description,
                "actions": actions,
                "history": history,
                "priority": priority
            },
            receive_id=receive_id
        )