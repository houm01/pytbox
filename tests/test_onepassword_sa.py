#!/usr/bin/env python3

import asyncio
from pytbox.onepassword_sa import OnePasswordClient


# 简单测试
async def main():
    """简单测试示例"""
    try:
        async with OnePasswordClient(vault_id="hcls5uxuq5dmxorw6rfewefdsa", integration_name='automate') as op:
            # items = await op.get_vault_items()
            # print(items)
            item = await op.get_item(item_id="f7eda4fgxfcukna7tpdpw7frlu")
            print(item)
            # r = await op.create_item(url="https://www.baidu.com", name="demo", username="demo", password="tssdseses", notes='test')
            # print(r)
            # items = await op.get_vault_items(filter='title eq "demo"')
            # print(items)
    except Exception as e:
        print(f"❌ 错误: {e}")
        print(f"💡 可能的原因: vault_id 或 item_id 不正确")


if __name__ == "__main__":
    asyncio.run(main())