#!/usr/bin/env python3

import os
import json
import uuid
import time
from typing import TYPE_CHECKING, Literal, Any

if TYPE_CHECKING:
    from .client import BaseClient
from ..schemas.response import ReturnResponse

class Endpoint:

    """
    Endpoint 类。

    用于 Endpoint 相关能力的封装。
    """
    def __init__(self, parent: "BaseClient") -> None:
        """
        初始化对象。

        Args:
            parent: parent 参数。
        """
        self.parent = parent


class AuthEndpoint(Endpoint):

    """
    AuthEndpoint 类。

    用于 Auth Endpoint 相关能力的封装。
    """
    token_path = "/tmp/.feishu_token.json"

    def save_token_to_file(self) -> ReturnResponse:
        """
        保存token to file。

        Returns:
            Any: 返回值。
        """
        refresh_resp = self.parent.token_provider.refresh()
        if refresh_resp.code != 0:
            return refresh_resp
        return ReturnResponse(code=0, msg="token refreshed and persisted", data=refresh_resp.data)
    
    def fetch_token_from_file(self) -> ReturnResponse:
        """
        获取token from file。

        Returns:
            Any: 返回值。
        """
        return self.parent.token_provider.peek_file_token()

    def get_tenant_access_token(self) -> ReturnResponse:
        '''
        _summary_

        Returns:
            _type_: _description_
        '''
        return self.parent.token_provider.get_token()

    def refresh_access_token(self) -> ReturnResponse:
        """
        刷新access token。

        Returns:
            Any: 返回值。
        """
        return self.parent.token_provider.refresh()

class MessageEndpoint(Endpoint):

    """
    MessageEndpoint 类。

    用于 Message Endpoint 相关能力的封装。
    """
    def send_text(self,
                  text: str,
                  receive_id: str):
        

        """
        发送text。

        Args:
            text: text 参数。
            receive_id: 资源 ID。

        Returns:
            Any: 返回值。
        """
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
    
    def send_post(
        self,
        receive_id: str = None,
        message_id: str = None,
        title: str = None,
        content: list = None,
    ) -> ReturnResponse:
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
        else:
            return ReturnResponse(code=1001, msg="receive_id 或 message_id 必填", data=None)

        return self.parent.request(path=api, method='POST', body=payload)

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

    def send_file(self, file_name: str, file_path: str, receive_id: str) -> ReturnResponse:
        """
        发送file。

        Args:
            file_name: file_name 参数。
            file_path: file_path 参数。
            receive_id: 资源 ID。

        Returns:
            Any: 返回值。
        """
        receive_id_type = self.parent.extensions.parse_receive_id_type(receive_id=receive_id)
        upload_resp = self.parent.extensions.upload_file(file_name=file_name, file_path=file_path)
        if upload_resp.code != 0:
            return upload_resp

        upload_data = upload_resp.data if isinstance(upload_resp.data, dict) else {}
        file_key = upload_data.get("file_key")
        if not file_key:
            return ReturnResponse(code=4001, msg="上传文件成功但未返回 file_key", data=upload_resp.data)

        content = {"file_key": file_key}
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
    
    def reply(self, message_id: str, content: str) -> ReturnResponse:
        """
        执行 reply 相关逻辑。

        Args:
            message_id: 资源 ID。
            content: content 参数。

        Returns:
            Any: 返回值。
        """
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
            path=f"/im/v1/messages/{message_id}/reply",
            method='POST',
            body=payload
        )
    
    def forward(self, message_id: str, receive_id: str) -> ReturnResponse:
        """
        执行 forward 相关逻辑。

        Args:
            message_id: 资源 ID。
            receive_id: 资源 ID。

        Returns:
            Any: 返回值。
        """
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
            path=f"/im/v1/messages/{message_id}/reactions",
            method='POST',
            body=payload
        )
        if r.code == 0:
            return ReturnResponse(code=0, msg=f"{message_id} 回复 emoji [{emoji_type}] 成功")
        else:
            return ReturnResponse(code=1, msg=f"{message_id} 回复 emoji [{emoji_type}] 失败")

    def webhook_send_feishu_card(
        self,
        webhook_url: str,
        template_id: str = None,
        template_version: str = '1.0.0',
        template_variable: dict = None,
    ) -> ReturnResponse:
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

        if template_variable is None:
            template_variable = {}

        headers = {
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
        return self.parent.request(
            path=webhook_url,
            method='POST',
            body=payload,
            headers=headers,
            use_auth=False,
        )


class BitableEndpoint(Endpoint):
    
    """
    BitableEndpoint 类。

    用于 Bitable Endpoint 相关能力的封装。
    """
    def list_records(
        self,
        app_token,
        table_id,
        field_names: list = None,
        automatic_fields: bool = False,
        filter_conditions: list = None,
        conjunction: Literal['and', 'or'] = 'and',
        sort_field_name: str = None,
        view_id: str = None,
    ) -> ReturnResponse:
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
            
        records = self.parent.request(
            path=f'/bitable/v1/apps/{app_token}/tables/{table_id}/records/search',
            method='POST',
            body=payload,
        )
        if records.code != 0:
            return records

        data = records.data if isinstance(records.data, dict) else {}
        rows = data.get("items", [])
        parsed_rows: list[dict[str, Any]] = []
        for item in rows:
            row: dict[str, Any] = {}
            for key, value in item.get('fields', {}).items():
                if isinstance(value, list):
                    try:
                        value = value[0].get('text')
                    except AttributeError:
                        pass
                row[key] = value
            parsed_rows.append(row)
        return ReturnResponse(code=0, msg="查询记录成功", data=parsed_rows)
    
    def add_record(self, app_token, table_id, fields):
        """
        新增record。

        Args:
            app_token: app_token 参数。
            table_id: 资源 ID。
            fields: fields 参数。

        Returns:
            Any: 返回值。
        """
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

    def query_record_id(
        self,
        app_token: str = None,
        table_id: str = None,
        filter_field_name: str = None,
        filter_value: str = None,
    ) -> ReturnResponse:
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
        if res.code != 0:
            return ReturnResponse(code=res.code, msg="查询记录 ID 失败", data=res.data)

        data = res.data if isinstance(res.data, dict) else {}
        items = data.get("items", [])
        if not items:
            return ReturnResponse(code=0, msg="未找到记录", data={"record_id": None})
        return ReturnResponse(code=0, msg="查询记录 ID 成功", data={"record_id": items[0].get("record_id")})
        
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
        query_id_resp = self.query_record_id(app_token, table_id, filter_field_name, filter_value)
        if query_id_resp.code != 0:
            return query_id_resp

        query_data = query_id_resp.data if isinstance(query_id_resp.data, dict) else {}
        record_id = query_data.get("record_id")

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

    def query_name_by_record_id(
        self,
        app_token: str = None,
        table_id: str = None,
        field_names: list = None,
        record_id: str = '',
        name: str = '',
    ) -> ReturnResponse:
        """
        查询name by record id。

        Args:
            app_token: app_token 参数。
            table_id: 资源 ID。
            field_names: field_names 参数。
            record_id: 资源 ID。
            name: name 参数。

        Returns:
            Any: 返回值。
        """
        response = self.query_record(app_token=app_token, table_id=table_id, field_names=field_names)
        if response.code == 0:
            data = response.data if isinstance(response.data, dict) else {}
            for item in data.get('items', []):
                if item['record_id'] == record_id:
                    parsed = self.parent.extensions.parse_bitable_data(item['fields'], name)
                    return ReturnResponse(code=0, msg="查询字段成功", data={"value": parsed})
            return ReturnResponse.no_data(msg="未找到匹配记录")
        return ReturnResponse(code=response.code, msg="查询字段失败", data=response.data)

class DocsEndpoint(Endpoint):

    """
    DocsEndpoint 类。

    用于 Docs Endpoint 相关能力的封装。
    """
    def rename_doc_title(self, space_id, node_token, title):
        """
        执行 rename doc title 相关逻辑。

        Args:
            space_id: 资源 ID。
            node_token: node_token 参数。
            title: title 参数。

        Returns:
            Any: 返回值。
        """
        payload = {
            "title": title
        }
        return self.parent.request(path=f'/wiki/v2/spaces/{space_id}/nodes/{node_token}/update_title',
                                   method='POST',
                                   body=payload)

    def create_doc(self, space_id: str, parent_node_token: str, title: str) -> ReturnResponse:
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
        if res.code != 0:
            return res

        data = res.data if isinstance(res.data, dict) else {}
        node = data.get("node", {})
        node_token = node.get("node_token")
        if not node_token:
            return ReturnResponse(code=4001, msg="创建文档成功但缺少 node_token", data=res.data)
        rename_resp = self.rename_doc_title(space_id=space_id, node_token=node_token, title=title)
        if rename_resp.code != 0:
            return rename_resp
        return res

    def create_block(
        self,
        document_id: str = None,
        block_id: str = None,
        client_token: str = None,
        payload: dict = None,
    ) -> ReturnResponse:
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
        payload = payload or {}

        children = payload.get('children')

        if payload.get('children_id'):
            # 创建嵌套块, 参考文档 
            # https://open.feishu.cn/api-explorer/cli_a1ae749cd7f9100d?apiName=create&from=op_doc_tab&project=docx&resource=document.block.descendant&version=v1
            return self.parent.request(path=f'/docx/v1/documents/{document_id}/blocks/{block_id}/descendant',
                                    method='POST',
                                    body=payload)
        elif isinstance(children, list) and children and children[0].get('block_type') == 27:
            
            r = self.parent.request(path=f'/docx/v1/documents/{document_id}/blocks/{block_id}/children',
                                    method='POST',
                                    body=payload)
            data = r.data if isinstance(r.data, dict) else {}
            children = data.get("children", [])
            if not children:
                return ReturnResponse(code=4001, msg="创建图片块失败：缺少 children", data=r.data)
            block_id = children[0].get('block_id')
            if not block_id:
                return ReturnResponse(code=4001, msg="创建图片块失败：缺少 block_id", data=r.data)
            
            media_resp = self.parent.extensions.upload_media(
                file_path=payload['file_path'],
                block_id=block_id
            )
            if media_resp.code != 0:
                return media_resp
            media_data = media_resp.data if isinstance(media_resp.data, dict) else {}
            file_token = media_data.get("file_token")
            if not file_token:
                return ReturnResponse(code=4001, msg="上传媒体成功但缺少 file_token", data=media_resp.data)
            
            res = self.update_block(
                document_id=document_id,
                block_id=block_id,
                replace_image_token=file_token,
                image_width=payload['image_width'],
                image_height=payload['image_height'],
                image_align=payload['image_align']
            )
            return res
        else:
            return self.parent.request(path=f'/docx/v1/documents/{document_id}/blocks/{block_id}/children',
                                    method='POST',
                                    body=payload)
    
    def create_block_children(self, document_id: str=None, block_id: str=None, payload: dict=None):
        """
        创建block children。

        Args:
            document_id: 资源 ID。
            block_id: 资源 ID。
            payload: payload 参数。

        Returns:
            Any: 返回值。
        """
        return self.parent.request(path=f'/docx/v1/documents/{document_id}/blocks/{block_id}/children',
                                    method='POST',
                                    body=payload)

    def update_block(self, document_id: str=None, block_id: str=None, replace_image_token: str=None, image_width: int=100, image_height: int=100, image_align: int=2):
        """
        更新block。

        Args:
            document_id: 资源 ID。
            block_id: 资源 ID。
            replace_image_token: replace_image_token 参数。
            image_width: image_width 参数。
            image_height: image_height 参数。
            image_align: image_align 参数。

        Returns:
            Any: 返回值。
        """
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
    """
    CalendarEndpoint 类。

    用于 Calendar Endpoint 相关能力的封装。
    """
    def get_events(self, 
                   calendar_id: str='feishu.cn_dQ4cLmSfGa1QSWqv3EvpLf@group.calendar.feishu.cn', 
                   start_time: int=int(time.time()) - 30*24*60*60, 
                   end_time: int=int(time.time()), 
                   page_size: int=500,
                   anchor_time: int=None
                ):
        """
        获取events。

        Args:
            calendar_id: 资源 ID。
            start_time: start_time 参数。
            end_time: end_time 参数。
            page_size: page_size 参数。
            anchor_time: anchor_time 参数。

        Returns:
            Any: 返回值。
        """
        if anchor_time:
            anchor_time = f'&anchor_time={anchor_time}'
        else:
            anchor_time = ''
        return self.parent.request(path=f'/calendar/v4/calendars/{calendar_id}/events?anchor_time={start_time}&end_time={end_time}&page_size={page_size}&start_time={start_time}',
                                   method='GET')


class ExtensionsEndpoint(Endpoint):
    """
    ExtensionsEndpoint 类。

    用于 Extensions Endpoint 相关能力的封装。
    """
    def parse_receive_id_type(self, receive_id):
        """
        解析receive id type。

        Args:
            receive_id: 资源 ID。

        Returns:
            Any: 返回值。
        """
        if receive_id.startswith('ou'):
            receive_id_type = 'open_id'
        elif receive_id.startswith('oc'):
            receive_id_type = 'chat_id'
        else:
            raise ValueError('No such named receive_id')
        return receive_id_type

    def upload_file(self, file_name: str, file_path: str) -> ReturnResponse:

        """
        上传file。

        Args:
            file_name: file_name 参数。
            file_path: file_path 参数。

        Returns:
            Any: 返回值。
        """
        with open(file_path, 'rb') as file_obj:
            files = {
                'file': (file_name, file_obj, 'application/octet-stream'),
            }
            form_data = {
                'file_type': 'stream',
                'file_name': file_name,
            }
            response = self.parent.request(
                path='/im/v1/files',
                method='POST',
                files=files,
                data=form_data,
            )
        if response.code != 0:
            return response
        payload = response.data if isinstance(response.data, dict) else {}
        file_key = payload.get('file_key')
        if not file_key:
            return ReturnResponse(code=4001, msg='上传文件成功但未返回 file_key', data=response.data)
        return ReturnResponse(code=0, msg='上传文件成功', data={'file_key': file_key})

    def upload_image(self, image_path: str) -> ReturnResponse:
        """
        上传image。

        Args:
            image_path: image_path 参数。

        Returns:
            Any: 返回值。
        """
        with open(image_path, 'rb') as file_obj:
            files = {
                'image': ('image', file_obj, 'application/octet-stream'),
            }
            form_data = {
                'image_type': 'message',
            }
            response = self.parent.request(
                path='/im/v1/images',
                method='POST',
                files=files,
                data=form_data,
            )

        if response.code != 0:
            return response
        payload = response.data if isinstance(response.data, dict) else {}
        image_key = payload.get('image_key')
        if not image_key:
            return ReturnResponse(code=4001, msg='上传图片成功但未返回 image_key', data=response.data)
        return ReturnResponse(code=0, msg='上传图片成功', data={'image_key': image_key})
    
    
    def build_block_heading(self, content, heading_level: Literal[1, 2, 3, 4]):
        """
        构建block heading。

        Args:
            content: content 参数。
            heading_level: heading_level 参数。

        Returns:
            Any: 返回值。
        """
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
        """
        构建block element。

        Args:
            content: content 参数。
            background_color: background_color 参数。
            text_color: text_color 参数。

        Returns:
            Any: 返回值。
        """
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
        return result

    def build_bitable_text(self, text: str=None):
        """
        构建bitable text。

        Args:
            text: text 参数。

        Returns:
            Any: 返回值。
        """
        return {"title": text}

    def build_block_image(self, file_path, percent: int=100, image_align: int=2):

        """
        构建block image。

        Args:
            file_path: file_path 参数。
            percent: percent 参数。
            image_align: image_align 参数。

        Returns:
            Any: 返回值。
        """
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

    def upload_media(self, file_path: str, block_id: str) -> ReturnResponse:
        """
        上传media。

        Args:
            file_path: file_path 参数。
            block_id: 资源 ID。

        Returns:
            Any: 返回值。
        """
        file_size = os.path.getsize(file_path)
        with open(file_path, 'rb') as file_obj:
            files = {
                'file': (os.path.basename(file_path), file_obj, 'application/octet-stream'),
            }
            form_data = {
                'file_name': os.path.basename(file_path),
                'parent_type': 'docx_image',
                'parent_node': block_id,
                'size': str(file_size),
            }
            response = self.parent.request(
                path='/drive/v1/medias/upload_all',
                method='POST',
                files=files,
                data=form_data,
            )
        if response.code != 0:
            return response
        payload = response.data if isinstance(response.data, dict) else {}
        file_token = payload.get('file_token')
        if not file_token:
            return ReturnResponse(code=4001, msg='上传媒体成功但未返回 file_token', data=response.data)
        return ReturnResponse(code=0, msg='上传媒体成功', data={'file_token': file_token})
    
    def create_block(self, blocks: list, document_id: str) -> ReturnResponse:
            # 交换blocks中元素的顺序
        """
        创建block。

        Args:
            blocks: blocks 参数。
            document_id: 资源 ID。

        Returns:
            Any: 返回值。
        """
        blocks.reverse()
        
        for block in blocks:
            time.sleep(1)
            try:
                if block['children'][0]['block_type'] != 27:
                    create_resp = self.parent.docs.create_block(
                        document_id=document_id,
                        block_id=document_id,
                        payload=block
                    )
                    if create_resp.code != 0:
                        return create_resp
                        
                elif block['children'][0]['block_type'] == 27:
                    create_resp = self.parent.docs.create_block(
                        document_id=document_id,
                        block_id=document_id,
                        payload=block
                    )
                    if create_resp.code != 0:
                        return create_resp
                    create_data = create_resp.data if isinstance(create_resp.data, dict) else {}
                    children = create_data.get('children', [])
                    if not children:
                        return ReturnResponse(code=4001, msg='创建图片块失败：缺少 children', data=create_resp.data)
                    block_id = children[0].get('block_id')
                    if not block_id:
                        return ReturnResponse(code=4001, msg='创建图片块失败：缺少 block_id', data=create_resp.data)
                    
                    media_resp = self.upload_media(
                        file_path=block['file_path'],
                        block_id=block_id
                    )
                    if media_resp.code != 0:
                        return media_resp
                    media_data = media_resp.data if isinstance(media_resp.data, dict) else {}
                    file_token = media_data.get('file_token')
                    if not file_token:
                        return ReturnResponse(code=4001, msg='上传媒体成功但缺少 file_token', data=media_resp.data)
                    
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
                return ReturnResponse(code=4001, msg="无效 block 结构", data={"block": block})
        return ReturnResponse(code=0, msg="区块处理完成", data={})
    
    def parse_bitable_data(self, fields, name):
        """
        解析bitable data。

        Args:
            fields: fields 参数。
            name: name 参数。

        Returns:
            Any: 返回值。
        """
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
        """
        获取user info。

        Args:
            email: email 参数。
            mobile: mobile 参数。
            get: get 参数。

        Returns:
            Any: 返回值。
        """
        payload = {
            "include_resigned": True,
        }
        user_input = email or mobile or ""
        if email:
            payload['emails'] = [email]
            user_input = email
        
        if mobile:
            payload['mobiles'] = [mobile]
            user_input = mobile
        
        response = self.parent.request(path='/contact/v3/users/batch_get_id',
                                   method='POST',
                                   body=payload)
        if response.code != 0:
            return ReturnResponse(code=response.code, msg=f"获取时失败, 报错请见 data 字段", data=response.data)

        response_data = response.data if isinstance(response.data, dict) else {}
        user_list = response_data.get("user_list", [])
        if not user_list:
            return ReturnResponse.no_data(msg=f'根据用户输入的 {user_input}, 未找到用户')

        if get == 'open_id':
            user_id = user_list[0].get('user_id')
            return ReturnResponse(code=0, msg=f'根据用户输入的 {user_input}, 获取用户 open_id 成功', data={"user_id": user_id})
        return ReturnResponse(code=0, msg=f'根据用户输入的 {user_input}, 获取用户信息成功', data=response_data)
    
    def format_rich_text(self, text: str, color: Literal['red', 'green', 'yellow', 'blue'], bold: bool=False):
        """
        格式化rich text。

        Args:
            text: text 参数。
            color: color 参数。
            bold: bold 参数。

        Returns:
            Any: 返回值。
        """
        if bold:
            text = f"**{text}**"

        if color:
            text = f"<font color='{color}'>{text}</font>"
                    
        return text
    
    def convert_str_to_dict(self, text: str):
        """
        转换str to dict。

        Args:
            text: text 参数。

        Returns:
            Any: 返回值。
        """
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
            """
            遍历。

            Args:
                node: node 参数。

            Returns:
                Any: 返回值。
            """
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
   
    def send_message_notify(
        self,
        receive_id: str='ou_ca3fc788570865cbbf59bfff43621a78',
        color: Literal['red', 'green', 'blue']='red',
        title: str='Test',
        sub_title: str='未填写子标题',
        priority: str='P0',
        content: str='Test',
    ) -> ReturnResponse:
        """
        发送message notify。

        Args:
            receive_id: 资源 ID。
            color: color 参数。
            title: title 参数。
            sub_title: sub_title 参数。
            priority: priority 参数。
            content: content 参数。

        Returns:
            Any: 返回值。
        """
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
    
    def get_user_info_by_open_id(self, open_id: str, get: Literal['name', 'all']='all') -> ReturnResponse:
        """
        获取user info by open id。

        Args:
            open_id: 资源 ID。
            get: get 参数。

        Returns:
            Any: 返回值。
        """
        response = self.parent.request(path=f'/contact/v3/users/{open_id}?department_id_type=open_department_id&user_id_type=open_id',
                                   method='GET')
        if response.code != 0:
            return ReturnResponse(code=response.code, msg="查询用户失败", data=response.data)
        payload = response.data if isinstance(response.data, dict) else {}
        user = payload.get("user", {})
        if get == 'name':
            return ReturnResponse(code=0, msg="查询用户名成功", data={"name": user.get("name")})
        return ReturnResponse(code=0, msg="查询用户成功", data=payload)
    
    def send_alert_notify(
        self,
        event_content: str=None,
        event_name: str=None,
        entity_name: str=None,
        event_time: str=None,
        resolved_time: str='',
        event_description: str=None,
        actions: str=None,
        history: str=None,
        color: Literal['red', 'green', 'blue']='red',
        priority: Literal['P0', 'P1', 'P2', 'P3', 'P4']='P2',
        receive_id: str=None,
    ) -> ReturnResponse:
        """
        发送alert notify。

        Args:
            event_content: event_content 参数。
            event_name: event_name 参数。
            entity_name: entity_name 参数。
            event_time: event_time 参数。
            resolved_time: resolved_time 参数。
            event_description: event_description 参数。
            actions: actions 参数。
            history: history 参数。
            color: color 参数。
            priority: priority 参数。
            receive_id: 资源 ID。

        Returns:
            Any: 返回值。
        """
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
        }
        # 移除 value 为 None 的键
        template_variable = {k: v for k, v in template_variable.items() if v is not None}
        
        return self.parent.message.send_card(
            template_id="AAqXPIkIOW0g9",
            template_variable=template_variable,
            receive_id=receive_id
        )
