#!/usr/bin/env python3

import requests
from .utils.response import ReturnResponse


class Notion:
    '''
    Notion API 简单封装类
    '''
    def __init__(self, token: str, proxy: str = None, timeout: int=10):
        self.token = token
        self.headers = {
            "accept": "application/json",
            "Notion-Version": "2022-06-28",
            "content-type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        self.timeout = timeout
        self.proxy = proxy
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.proxies.update({"http": self.proxy, "https": self.proxy})
        self.base_url = "https://api.notion.com/v1"
    
    def database_create(self, page_id: str, name: str = "test databse") -> ReturnResponse:
        """
        在指定的 page 下创建一个简单的数据库
        
        Args:
            page_id: 父页面的 ID（不需要带横杠）
            database_name: 数据库名称
            
        Returns:
            dict: API 响应结果
        """
        url = f"{self.base_url}/databases"

        payload = {
            "parent": {
                "type": "page_id",
                "page_id": page_id
            },
            "title": [
                {
                    "type": "text",
                    "text": {
                        "content": name
                    }
                }
            ],
            "properties": {
                "名称": {
                    "title": {}
                }
            }
        }
        
        response = self.session.post(url, json=payload, timeout=self.timeout)
        
        if response.status_code == 200:
            return ReturnResponse(code=0, msg=f"数据库创建成功: {name}", data=response.json())
        else:
            return ReturnResponse(code=1, msg=f"数据库创建失败: {response.status_code}", data=response.text)

    def database_update(self, db_id: str, title: str = None, description: str = None, icon: dict = None, cover: dict = None) -> ReturnResponse:
        """
        更新数据库属性
        
        Args:
            db_id: 数据库 ID
            title: 数据库标题
            description: 数据库描述
            icon: 数据库图标
            cover: 数据库封面
            
        Returns:
            ReturnResponse: 更新结果
        """
        url = f"{self.base_url}/databases/{db_id}"
        
        payload = {}
        
        # 构建更新字段
        if title is not None:
            payload["title"] = [
                {
                    "type": "text",
                    "text": {
                        "content": title
                    }
                }
            ]
        
        if description is not None:
            payload["description"] = [
                {
                    "type": "text", 
                    "text": {
                        "content": description
                    }
                }
            ]
            
        if icon is not None:
            payload["icon"] = icon
            
        if cover is not None:
            payload["cover"] = cover
        
        # 如果没有提供任何更新字段，返回错误
        if not payload:
            return ReturnResponse(code=1, msg="至少需要提供一个更新字段", data=None)
        
        response = self.session.patch(url, json=payload, timeout=self.timeout)
        
        if response.status_code == 200:
            return ReturnResponse(code=0, msg="数据库更新成功", data=response.json())
        else:
            return ReturnResponse(code=1, msg=f"数据库更新失败: {response.status_code}", data=response.text)

    def page_create(self, db_id: str, properties: dict = None) -> ReturnResponse:
        """
        在数据库中创建新页面（添加数据）
        
        Args:
            db_id: 数据库 ID
            properties: 页面属性字典，键为属性名，值为属性值
            
        Returns:
            ReturnResponse: 创建结果
        """
        url = f"{self.base_url}/pages"
        
        # 默认属性
        if properties is None:
            properties = {}
        
        # 构建请求体
        payload = {
            "parent": {
                "type": "database_id",
                "database_id": db_id
            },
            "properties": {}
        }
        
        # 处理属性
        for key, value in properties.items():
            payload["properties"][key] = self._format_property_value(key, value)
        
        response = self.session.post(url, json=payload, timeout=self.timeout)
        
        if response.status_code == 200:
            return ReturnResponse(code=0, msg="页面创建成功", data=response.json())
        else:
            return ReturnResponse(code=1, msg=f"页面创建失败: {response.status_code}", data=response.text)

    def page_update(self, page_id: str, properties: dict = None) -> ReturnResponse:
        """
        更新页面属性
        
        Args:
            page_id: 页面 ID
            properties: 页面属性字典
            
        Returns:
            ReturnResponse: 更新结果
        """
        url = f"{self.base_url}/pages/{page_id}"
        
        if properties is None:
            properties = {}
        
        # 构建请求体
        payload = {"properties": {}}
        
        # 处理属性
        for key, value in properties.items():
            payload["properties"][key] = self._format_property_value(key, value)
        
        response = self.session.patch(url, json=payload, timeout=self.timeout)
        
        if response.status_code == 200:
            return ReturnResponse(code=0, msg="页面更新成功", data=response.json())
        else:
            return ReturnResponse(code=1, msg=f"页面更新失败: {response.status_code}", data=response.text)

    def page_upsert(self, db_id: str, unique_field: str, unique_value: str, properties: dict = None, content: list = None) -> ReturnResponse:
        """
        智能创建或更新页面（Upsert操作）
        
        根据唯一字段查找页面：
        - 如果找到匹配的页面，则更新该页面的属性
        - 如果未找到匹配的页面，则创建新页面
        
        支持的属性类型：
        - 标题属性 (title): 字段名包含 name/title/名称/标题
        - 文本属性 (rich_text): 普通文本字段
        - 复选框属性 (checkbox): 布尔值
        - 数字属性 (number): 数字值
        - 多选属性 (multi_select): 字符串列表
        - 单选属性 (select): 字典格式 {"name": "选项名"}
        - 日期属性 (date): 字典格式 {"start": "2024-01-01"}
        - URL属性 (url): 字典格式 {"url": "https://example.com"}
        - 邮箱属性 (email): 字典格式 {"email": "test@example.com"}
        - 电话号码属性 (phone_number): 字典格式 {"phone_number": "123-456-7890"}
        - 状态属性 (status): 字典格式 {"name": "状态名"}
        - 关系属性 (relation): 支持多种格式
          * 直接ID: [{"id": "页面ID"}]
          * 便捷格式: [{"title": "页面标题", "database_id": "数据库ID"}]
          * 混合格式: [{"id": "页面ID1"}, {"title": "页面标题", "database_id": "数据库ID"}]
        - 人员属性 (people): 列表格式 [{"id": "用户ID"}] 或 [{"email": "邮箱"}]
        
        Args:
            db_id: 数据库 ID
            unique_field: 用于查找的唯一字段名（如"名称"、"Name"等）
            unique_value: 唯一字段的值，用于查找匹配的页面
            properties: 页面属性字典，包含要设置或更新的属性
            content: 页面内容列表，包含要添加的内容块
            
        Returns:
            ReturnResponse: 创建或更新结果
            - code=0: 操作成功
            - code=1: 操作失败，查看 msg 和 data 获取错误信息
            
        Example:
            # 第一次调用会创建新页面
            result = notion.page_upsert(
                db_id="database_id",
                unique_field="Name",
                unique_value="项目A",
                properties={
                    "Name": "项目A",
                    "Status": {"name": "进行中"},
                    "Priority": 1,
                    "Tags": ["重要", "紧急"],
                    # 关系字段便捷用法
                    "RelatedPages": [
                        {"title": "相关项目1", "database_id": "related_db_id"},
                        {"title": "相关项目2", "database_id": "related_db_id"}
                    ]
                },
                # 页面内容
                content=[
                    {"type": "heading_1", "text": "项目概述"},
                    {"type": "paragraph", "text": "这是项目的详细描述"},
                    {"type": "to_do", "text": "完成需求分析", "checked": True},
                    {"type": "to_do", "text": "设计系统架构", "checked": False}
                ]
            )
            
            # 第二次调用会更新现有页面
            result = notion.page_upsert(
                db_id="database_id",
                unique_field="Name", 
                unique_value="项目A",  # 相同的唯一值
                properties={
                    "Name": "项目A",
                    "Status": {"name": "已完成"},  # 更新状态
                    "Priority": 2,  # 更新优先级
                    # 混合关系字段格式
                    "RelatedPages": [
                        {"id": "existing_page_id"},  # 直接ID
                        {"title": "新相关项目", "database_id": "related_db_id"}  # 便捷格式
                    ]
                },
                # 更新页面内容
                content=[
                    {"type": "heading_2", "text": "更新内容"},
                    {"type": "paragraph", "text": "项目状态已更新"},
                    {"type": "quote", "text": "项目进展顺利"}
                ]
            )
        """
        if properties is None:
            properties = {}
        if content is None:
            content = []
        
        # 1. 先查询数据库，看是否存在相同记录
        query_url = f"{self.base_url}/databases/{db_id}/query"
        query_payload = {
            "filter": {
                "property": unique_field,
                "title": {
                    "equals": unique_value
                }
            }
        }
        
        query_response = self.session.post(query_url, json=query_payload, timeout=self.timeout)
        
        if query_response.status_code == 200:
            results = query_response.json().get("results", [])
            
            if results:
                # 找到记录，执行更新
                page_id = results[0]["id"]
                
                # 更新页面属性
                update_result = self.page_update(page_id, properties)
                
                # 如果有内容需要添加，则添加内容
                if content and update_result.code == 0:
                    content_result = self.page_add_content(page_id, content)
                    if content_result.code == 0:
                        return content_result
                    else:
                        return update_result
                else:
                    return update_result
            else:
                # 未找到记录，执行创建
                # 确保唯一字段包含在属性中
                if unique_field not in properties:
                    properties[unique_field] = unique_value
                
                # 创建页面
                create_result = self.page_create(db_id, properties)
                
                # 如果有内容需要添加，则添加内容
                if content and create_result.code == 0:
                    page_id = create_result.data["id"]
                    content_result = self.page_add_content(page_id, content)
                    if content_result.code == 0:
                        return content_result
                    else:
                        return create_result
                else:
                    return create_result
        else:
            # 查询失败，直接尝试创建
            if unique_field not in properties:
                properties[unique_field] = unique_value
            
            # 创建页面
            create_result = self.page_create(db_id, properties)
            
            # 如果有内容需要添加，则添加内容
            if content and create_result.code == 0:
                page_id = create_result.data["id"]
                content_result = self.page_add_content(page_id, content)
                if content_result.code == 0:
                    return content_result
                else:
                    return create_result
            else:
                return create_result

    def _find_page_by_title(self, db_id: str, title: str) -> str:
        """
        根据标题在数据库中查找页面ID
        
        Args:
            db_id: 数据库ID
            title: 页面标题
            
        Returns:
            str: 页面ID，如果未找到返回None
        """
        query_url = f"{self.base_url}/databases/{db_id}/query"
        query_payload = {
            "filter": {
                "property": "Name",  # 假设标题字段名为"Name"
                "title": {
                    "equals": title
                }
            }
        }
        
        response = self.session.post(query_url, json=query_payload, timeout=self.timeout)
        
        if response.status_code == 200:
            results = response.json().get("results", [])
            if results:
                return results[0]["id"]
        
        return None

    def _format_relation_value(self, value) -> list:
        """
        格式化关系属性值，支持多种输入格式
        
        Args:
            value: 关系值，支持以下格式：
                - 字符串: 页面标题，需要指定database_id
                - 字典: {"title": "页面标题", "database_id": "数据库ID"}
                - 列表: [{"title": "标题1", "database_id": "数据库ID1"}, ...]
                - 列表: [{"id": "页面ID1"}, {"id": "页面ID2"}]
                
        Returns:
            list: 格式化后的关系值列表
        """
        if isinstance(value, str):
            # 字符串格式，需要database_id
            raise ValueError("字符串格式需要同时提供database_id，请使用字典格式：{'title': '页面标题', 'database_id': '数据库ID'}")
        
        elif isinstance(value, dict):
            if "id" in value:
                # 直接提供页面ID
                return [{"id": value["id"]}]
            elif "title" in value and "database_id" in value:
                # 提供标题和数据库ID，需要查找页面ID
                page_id = self._find_page_by_title(value["database_id"], value["title"])
                if page_id:
                    return [{"id": page_id}]
                else:
                    raise ValueError(f"未找到标题为 '{value['title']}' 的页面")
            else:
                raise ValueError("字典格式必须包含 'id' 或 ('title' 和 'database_id')")
        
        elif isinstance(value, list):
            relation_result = []
            for item in value:
                if isinstance(item, str):
                    raise ValueError("列表中的字符串需要提供database_id")
                elif isinstance(item, dict):
                    if "id" in item:
                        relation_result.append({"id": item["id"]})
                    elif "title" in item and "database_id" in item:
                        page_id = self._find_page_by_title(item["database_id"], item["title"])
                        if page_id:
                            relation_result.append({"id": page_id})
                        else:
                            raise ValueError(f"未找到标题为 '{item['title']}' 的页面")
                    else:
                        raise ValueError("列表项必须包含 'id' 或 ('title' 和 'database_id')")
                else:
                    raise ValueError("列表项必须是字典格式")
            return relation_result
        
        else:
            raise ValueError("不支持的关系值格式")

    def _format_property_value(self, key: str, value) -> dict:
        """
        根据属性类型格式化属性值
        
        Args:
            key: 属性名
            value: 属性值
            
        Returns:
            dict: 格式化后的属性值
        """
        if isinstance(value, str):
            # 根据字段名判断属性类型
            if key.lower() in ['name', 'title', '名称', '标题']:
                # 标题属性
                return {
                    "title": [
                        {
                            "type": "text",
                            "text": {
                                "content": value
                            }
                        }
                    ]
                }
            else:
                # 文本属性 (rich_text)
                return {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": value
                            }
                        }
                    ]
                }
        elif isinstance(value, bool):
            # 复选框属性
            return {"checkbox": value}
        elif isinstance(value, (int, float)):
            # 数字属性
            return {"number": value}
        elif isinstance(value, list):
            # 列表类型，需要进一步判断
            if not value:
                # 空列表，默认作为多选处理
                return {"multi_select": []}
            
            # 根据第一个元素的类型判断
            first_item = value[0]
            if isinstance(first_item, str):
                # 多选属性
                return {
                    "multi_select": [
                        {"name": item} for item in value
                    ]
                }
            elif isinstance(first_item, dict):
                # 复杂对象列表
                if "name" in first_item:
                    # 多选属性
                    return {"multi_select": value}
                elif "id" in first_item or "title" in first_item:
                    # 关系属性
                    try:
                        return {"relation": self._format_relation_value(value)}
                    except ValueError:
                        return {"relation": value}  # 回退到原始值
                elif "email" in first_item:
                    # 人员属性
                    return {"people": value}
                elif "object" in first_item and first_item["object"] == "user":
                    # 人员属性（用户对象格式）
                    return {"people": value}
            return {"multi_select": [{"name": str(item)} for item in value]}
        elif isinstance(value, dict):
            # 字典类型
            if "start" in value:
                # 日期属性
                return {"date": value}
            elif "name" in value:
                # 单选属性
                return {"select": value}
            elif "url" in value:
                # URL属性
                return {"url": value["url"]}
            elif "email" in value:
                # 邮箱属性
                return {"email": value["email"]}
            elif "phone_number" in value:
                # 电话号码属性
                return {"phone_number": value["phone_number"]}
            elif "status" in value:
                # 状态属性
                return {"status": value}
            elif "id" in value or "title" in value:
                # 关系属性
                try:
                    return {"relation": self._format_relation_value(value)}
                except ValueError:
                    return {"relation": value}  # 回退到原始值
            else:
                # 默认作为单选处理
                return {"select": value}
        else:
            # 其他类型，转换为字符串处理
            return {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": str(value)
                        }
                    }
                ]
            }

    def page_add_content(self, page_id: str, content: list) -> ReturnResponse:
        """
        向页面添加内容块
        
        Args:
            page_id: 页面 ID
            content: 内容块列表，每个元素是一个内容块
            
        Returns:
            ReturnResponse: 添加结果
        """
        url = f"{self.base_url}/blocks/{page_id}/children"
        
        # 格式化内容块
        formatted_blocks = []
        for block in content:
            formatted_blocks.append(self._format_content_block(block))
        
        payload = {"children": formatted_blocks}
        
        response = self.session.patch(url, json=payload, timeout=self.timeout)
        
        if response.status_code == 200:
            return ReturnResponse(code=0, msg="页面内容添加成功", data=response.json())
        else:
            return ReturnResponse(code=1, msg=f"页面内容添加失败: {response.status_code}", data=response.text)

    def _format_content_block(self, block: dict) -> dict:
        """
        格式化内容块
        
        Args:
            block: 内容块字典，格式如：
                {
                    "type": "paragraph",
                    "text": "这是段落文本"
                }
                或
                {
                    "type": "heading_1",
                    "text": "这是一级标题"
                }
                
        Returns:
            dict: 格式化后的内容块
        """
        block_type = block.get("type", "paragraph")
        text = block.get("text", "")
        
        # 基础文本内容
        text_content = {
            "type": "text",
            "text": {
                "content": text
            }
        }
        
        # 根据类型返回不同的块结构
        if block_type == "paragraph":
            return {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [text_content]
                }
            }
        elif block_type == "heading_1":
            return {
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [text_content]
                }
            }
        elif block_type == "heading_2":
            return {
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [text_content]
                }
            }
        elif block_type == "heading_3":
            return {
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [text_content]
                }
            }
        elif block_type == "bulleted_list_item":
            return {
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [text_content]
                }
            }
        elif block_type == "numbered_list_item":
            return {
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": [text_content]
                }
            }
        elif block_type == "to_do":
            checked = block.get("checked", False)
            return {
                "type": "to_do",
                "to_do": {
                    "rich_text": [text_content],
                    "checked": checked
                }
            }
        elif block_type == "quote":
            return {
                "type": "quote",
                "quote": {
                    "rich_text": [text_content]
                }
            }
        elif block_type == "code":
            language = block.get("language", "plain text")
            return {
                "type": "code",
                "code": {
                    "rich_text": [text_content],
                    "language": language
                }
            }
        else:
            # 默认作为段落处理
            return {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [text_content]
                }
            }

if __name__ == "__main__":
    # 使用示例
    notion = Notion(token="your_integration_token_here")
    database_id = "your_database_id_here"
    
    # 使用智能创建/更新方法
    # 第一次调用会创建新记录
    result = notion.page_upsert(
        db_id=database_id,
        unique_field="名称",  # 用于查找的唯一字段
        unique_value="测试记录",  # 唯一字段的值
        properties={
            "名称": "测试记录",
            "状态": ["进行中"],
            "完成": False,
            "优先级": 1
        }
    )
    
    # 第二次调用会更新现有记录
    result = notion.page_upsert(
        db_id=database_id,
        unique_field="名称",
        unique_value="测试记录",  # 相同的唯一值
        properties={
            "名称": "测试记录",
            "状态": ["已完成"],  # 更新状态
            "完成": True,        # 更新完成状态
            "优先级": 2          # 更新优先级
        }
    )
    
    # 使用不同的唯一值会创建新记录
    result = notion.page_upsert(
        db_id=database_id,
        unique_field="名称",
        unique_value="新记录",
        properties={
            "名称": "新记录",
            "状态": ["待处理"],
            "完成": False,
            "优先级": 3
        }
    )