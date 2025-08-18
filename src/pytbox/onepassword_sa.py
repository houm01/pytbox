#!/usr/bin/env python3
"""
1Password 客户端封装类 - 异步版本（简化）
"""

import os
from typing import Optional, Dict, Any, List, Literal
try:
    from onepassword.client import Client
    from onepassword import (
        ItemCreateParams, ItemCategory, ItemField, ItemFieldType,
        ItemSection, Website, AutofillBehavior
    )
except ImportError:
    print("⚠️  请安装 1password SDK: pip install onepassword")
    Client = None


class OnePasswordClient:
    """1Password 客户端封装类"""
    
    def __init__(self, service_account_token: str = None, integration_name: str = "pytbox", integration_version: str = "v1.0.0", vault_id: str = None):
        """
        初始化 1Password 客户端
        
        Args:
            service_account_token: 服务账户令牌，如果不提供则从环境变量 OP_SERVICE_ACCOUNT_TOKEN 获取
            integration_name: 集成名称
            integration_version: 集成版本
            vault_id: 默认保险库ID
        """
        self.token = service_account_token or os.getenv("OP_SERVICE_ACCOUNT_TOKEN")
        self.integration_name = integration_name
        self.integration_version = integration_version
        self.vault_id = vault_id
        self.client: Optional[Client] = None
        
        if not self.token:
            raise ValueError("未找到 1Password 服务账户令牌，请设置 OP_SERVICE_ACCOUNT_TOKEN 环境变量或传入 service_account_token 参数")
        
        if Client is None:
            raise ImportError("未安装 onepassword SDK，请运行: pip install onepassword")
        
        # print(f"🔧 初始化1Password客户端:")
        # print(f"  - 集成名称: {self.integration_name}")
        # print(f"  - 默认保险库ID: {self.vault_id}")
        # print(f"  - 令牌: {'已设置' if self.token else '未设置'}")
    
    async def authenticate(self) -> None:
        """认证并初始化客户端"""
        if not self.client:
            self.client = await Client.authenticate(
                auth=self.token,
                integration_name=self.integration_name,
                integration_version=self.integration_version
            )
            # print(f"✅ 1Password 客户端认证成功")
    
    async def ensure_authenticated(self) -> None:
        """确保客户端已认证"""
        if not self.client:
            await self.authenticate()
    
    async def create_item(self, url, name, username, password, notes, tags: list=[]):
        # Create an Item and add it to your vault.
        await self.ensure_authenticated()
        to_create = ItemCreateParams(
            title=name,
            category=ItemCategory.LOGIN,
            vault_id=self.vault_id,
            fields=[
                ItemField(
                    id="username",
                    title="username",
                    field_type=ItemFieldType.TEXT,
                    value=username,
                ),
                ItemField(
                    id="password",
                    title="password",
                    field_type=ItemFieldType.CONCEALED,
                    value=password,
                ),
            ],
            sections=[
                ItemSection(id="", title=""),
                ItemSection(id="totpsection", title=""),
            ],
            tags=tags,
            notes=notes,
            websites=[
                Website(
                    label="网站",
                    url=url,
                    autofillBehavior=AutofillBehavior.ANYWHEREONWEBSITE
                    # autofill_behavior=AutofillBehavior.NEVER,
                )
            ],
        )
        created_item = await self.client.items.create(to_create)
        return created_item
    
    async def get_item(self, item_id):
        # Retrieve an item from your vault.
        item = await self.client.items.get(self.vault_id, item_id)
        return item
    
    async def get_vault_items(self) -> List[Dict[str, Any]]:
        """
        获取保险库中的所有项目
        
        Args:
            vault_id: 保险库ID，如果不提供则使用默认的
            
        Returns:
            List[Dict]: 项目列表
        """
        await self.ensure_authenticated()
        return await self.client.items.list(value_id = self.vault_id)
    
    async def list_vaults(self) -> List[Dict[str, Any]]:
        """
        列出所有可用的保险库
        
        Returns:
            List[Dict]: 保险库列表
        """
        await self.ensure_authenticated()
        try:
            vaults = await self.client.vaults.list_all()
            print(f"📁 找到 {len(vaults)} 个保险库:")
            for i, vault in enumerate(vaults):
                print(f"  {i+1}. {vault.get('name', 'Unknown')} (ID: {vault.get('id', 'Unknown')})")
            return vaults
        except Exception as e:
            print(f"❌ 获取保险库列表失败: {e}")
            return []
    
    async def get_item_by_item_id(self, item_id: str, title: Literal['username', 'password', 'totp']) -> Dict[str, Any]:
        """
        根据标题获取项目
        
        Args:
            title: 项目标题
            vault_id: 保险库ID，如果不提供则使用默认的
            
        Returns:
            Dict: 项目信息，如果未找到返回None
        """
        r = await self.get_item(item_id=item_id)
        for field in r.fields:
            if title == 'totp':
                if 'TOTP' in field.id:
                    return field.details.content.code
            else:           
                if field.title == title:
                    return field.value
    
    async def search_items(self, query: str, vault_id: str = None) -> List[Dict[str, Any]]:
        """
        搜索项目
        
        Args:
            query: 搜索查询
            vault_id: 保险库ID，如果不提供则使用默认的
            
        Returns:
            List[Dict]: 搜索结果
        """
        await self.ensure_authenticated()
        vault = vault_id or self.vault_id
        if not vault:
            raise ValueError("必须提供 vault_id 或在初始化时设置默认 vault_id")
        
        items = await self.get_vault_items(vault)
        # 简单的标题匹配搜索
        return [item for item in items if query.lower() in item.get('title', '').lower()]
    
    async def close(self) -> None:
        """关闭客户端连接"""
        if self.client:
            # 如果SDK提供关闭方法，在这里调用
            self.client = None
            print("🔒 1Password 客户端连接已关闭")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.authenticate()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


if __name__ == "__main__":
    pass