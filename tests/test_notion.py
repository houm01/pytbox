#!/usr/bin/env python3

from pytbox.base import notion


def test_notion_database_create():
    """测试创建数据库"""
    result = notion.database_create(
        page_id="28198e6eea908013bca1ddcb0a2058af",
        name="测试数据库"
    )
    print(f"创建数据库结果: {result}")
    return result


def test_notion_page_upsert():
    """测试智能创建/更新页面"""
    # 假设数据库ID
    database_id = "5553e66eefb94d8db8e80767feb01d93"
    
    # 第一次调用会创建新记录（包含内容）
    result1 = notion.page_upsert(
        db_id=database_id,
        unique_field="Name",
        unique_value="智能测试记录",
        properties={
            "Name": "智能测试记录",
            "Type": { "name": "日常工作"}
        },
        content=[
            {"type": "heading_1", "text": "测试页面"},
            {"type": "paragraph", "text": "这是通过page_upsert创建的页面内容"},
            {"type": "to_do", "text": "测试任务1", "checked": True},
            {"type": "to_do", "text": "测试任务2", "checked": False}
        ]
    )
    print(f"第一次upsert结果: {result1}")
    
    # 第二次调用会更新现有记录（添加更多内容）
    # result2 = notion.page_upsert(
    #     db_id=database_id,
    #     unique_field="Name",
    #     unique_value="智能测试记录",  # 相同的唯一值
    #     properties={
    #         "Name": "智能测试记录",
    #         "Text": "demo01 - 已更新"
    #     },
    #     content=[
    #         {"type": "heading_2", "text": "更新内容"},
    #         {"type": "paragraph", "text": "这是更新后的页面内容"},
    #         {"type": "quote", "text": "测试进展顺利"},
    #         {"type": "code", "text": "print('Hello, Notion!')", "language": "python"}
    #     ]
    # )
    # print(f"第二次upsert结果: {result2}")
    
    # return result1, result2


def test_notion_properties_types():
    """测试各种属性类型"""
    database_id = "28198e6eea9081769d5ee490124ae0fd"
    
    # 测试各种属性类型
    result = notion.page_create(
        db_id=database_id,
        properties={
            "Name": "属性类型测试",           # 标题属性
            "Description": "这是一个测试",    # 文本属性 (rich_text)
            "Completed": True,               # 复选框属性
            "Priority": 1,                   # 数字属性
            "Tags": ["重要", "紧急"],        # 多选属性
            "Status": {"name": "进行中"},     # 单选属性
            "DueDate": {"start": "2024-01-01"},  # 日期属性
            "Website": {"url": "https://example.com"},  # URL属性
            "Email": {"email": "test@example.com"},     # 邮箱属性
            "Phone": {"phone_number": "123-456-7890"},  # 电话号码属性
            "RelatedPages": [{"id": "page_id_1"}, {"id": "page_id_2"}],  # 关系属性（直接ID）
            "Assignees": [{"id": "user_id_1"}, {"id": "user_id_2"}]      # 人员属性
        }
    )
    print(f"属性类型测试结果: {result}")
    return result


def test_notion_relation_easy():
    """测试关系字段的便捷用法"""
    database_id = "28198e6eea9081769d5ee490124ae0fd"
    related_database_id = "related_database_id_here"  # 被链接的数据库ID
    
    # 测试关系字段的便捷用法
    result = notion.page_create(
        db_id=database_id,
        properties={
            "Name": "关系字段测试",
            "Description": "测试关系字段的便捷用法",
            # 便捷的关系字段用法：通过标题和数据库ID自动查找页面ID
            "RelatedPages": [
                {"title": "相关页面1", "database_id": related_database_id},
                {"title": "相关页面2", "database_id": related_database_id}
            ],
            # 也可以混合使用：直接ID + 标题查找
            "MixedRelations": [
                {"id": "existing_page_id"},  # 直接提供页面ID
                {"title": "通过标题查找", "database_id": related_database_id}  # 通过标题查找
            ]
        }
    )
    print(f"关系字段便捷用法测试结果: {result}")
    return result


def test_notion_page_upsert_with_content():
    """测试带内容的页面upsert"""
    database_id = "28198e6eea9081769d5ee490124ae0fd"
    
    # 测试完整的页面upsert（属性 + 内容）
    result = notion.page_upsert(
        db_id=database_id,
        unique_field="Name",
        unique_value="完整测试页面",
        properties={
            "Name": "完整测试页面",
            "Description": "这是一个包含完整内容的测试页面",
            "Status": {"name": "进行中"},
            "Priority": 1,
            "Tags": ["测试", "完整"]
        },
        content=[
            {"type": "heading_1", "text": "项目概述"},
            {"type": "paragraph", "text": "这是一个完整的项目页面，包含详细的描述和任务列表。"},
            {"type": "heading_2", "text": "任务列表"},
            {"type": "to_do", "text": "需求分析", "checked": True},
            {"type": "to_do", "text": "系统设计", "checked": True},
            {"type": "to_do", "text": "开发实现", "checked": False},
            {"type": "to_do", "text": "测试验证", "checked": False},
            {"type": "heading_2", "text": "技术栈"},
            {"type": "bulleted_list_item", "text": "Python 3.8+"},
            {"type": "bulleted_list_item", "text": "Notion API"},
            {"type": "bulleted_list_item", "text": "Requests库"},
            {"type": "heading_2", "text": "代码示例"},
            {"type": "code", "text": "from pytbox.notion import Notion\n\nnotion = Notion(token='your_token')\nresult = notion.page_upsert(\n    db_id='database_id',\n    unique_field='Name',\n    unique_value='测试页面',\n    properties={'Name': '测试页面'},\n    content=[{'type': 'paragraph', 'text': 'Hello, Notion!'}]\n)", "language": "python"},
            {"type": "heading_2", "text": "重要说明"},
            {"type": "quote", "text": "这个页面展示了如何使用page_upsert方法同时设置页面属性和添加页面内容。"}
        ]
    )
    print(f"完整页面upsert测试结果: {result}")
    return result


def test_notion_page_content():
    """测试向页面添加内容"""
    # 假设页面ID
    page_id = "your_page_id_here"
    
    # 定义页面内容
    content = [
        {
            "type": "heading_1",
            "text": "项目概述"
        },
        {
            "type": "paragraph",
            "text": "这是一个测试项目的概述内容。"
        },
        {
            "type": "heading_2",
            "text": "任务列表"
        },
        {
            "type": "to_do",
            "text": "完成需求分析",
            "checked": True
        },
        {
            "type": "to_do",
            "text": "设计系统架构",
            "checked": False
        },
        {
            "type": "bulleted_list_item",
            "text": "使用Python开发"
        },
        {
            "type": "bulleted_list_item",
            "text": "集成Notion API"
        },
        {
            "type": "quote",
            "text": "这是一个引用块，用于突出重要信息。"
        },
        {
            "type": "code",
            "text": "print('Hello, Notion!')",
            "language": "python"
        }
    ]
    
    result = notion.page_add_content(page_id, content)
    print(f"页面内容添加结果: {result}")
    return result


def test_notion_complete_workflow():
    """测试完整的Notion工作流程"""
    print("=== 开始完整工作流程测试 ===")
    
    # 1. 创建数据库
    print("\n1. 创建数据库...")
    create_result = test_notion_database_create()
    
    if create_result.code == 0:
        database_id = create_result.data["id"]
        print(f"数据库创建成功，ID: {database_id}")
        
        # 2. 添加包含各种属性类型的页面
        print("\n2. 添加页面（测试属性类型）...")
        page_result = test_notion_properties_types()
        
        if page_result.code == 0:
            page_id = page_result.data["id"]
            print(f"页面创建成功，ID: {page_id}")
            
            # 3. 向页面添加内容
            print("\n3. 向页面添加内容...")
            # 更新测试中的页面ID
            notion.page_add_content(page_id, [
                {
                    "type": "heading_1",
                    "text": "项目详情"
                },
                {
                    "type": "paragraph",
                    "text": "这是通过API添加的页面内容。"
                },
                {
                    "type": "to_do",
                    "text": "测试任务1",
                    "checked": True
                },
                {
                    "type": "to_do",
                    "text": "测试任务2",
                    "checked": False
                }
            ])
        
        # 4. 测试智能upsert
        print("\n4. 测试智能upsert...")
        upsert_result = notion.page_upsert(
            db_id=database_id,
            unique_field="Name",
            unique_value="工作流程测试",
            properties={
                "Name": "工作流程测试",
                "Description": "这是一个完整工作流程的测试记录",
                "Completed": False,
                "Priority": 3
            }
        )
        print(f"Upsert结果: {upsert_result}")
        
    else:
        print("数据库创建失败，跳过后续测试")
    
    print("\n=== 完整工作流程测试结束 ===")


if __name__ == "__main__":
    # 运行单个测试
    # test_notion_database_create()
    test_notion_page_upsert()
    # test_notion_properties_types()
    # test_notion_relation_easy()
    # test_notion_page_upsert_with_content()
    # test_notion_page_content()
    
    # 运行完整工作流程测试
    # test_notion_complete_workflow()
