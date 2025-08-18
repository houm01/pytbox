#!/usr/bin/env python3

from typing import List
from onepasswordconnectsdk.client import new_client_from_environment
from onepasswordconnectsdk.models import (Item, Field)


class OnePasswordConnect:
    '''tbd'''
    def __init__(self, vault_id):
        self.client = new_client_from_environment()
        self.vault_id = vault_id

    def create_item(self, name, username: str=None, password: str=None, notes: str="create by automation", tags: List=None):
        # Create an item
        new_item = Item(
            title=name,
            category="LOGIN",
            tags=tags,
            fields=[
                Field(value=username, purpose="USERNAME"),
                Field(value=password, purpose="PASSWORD"),
                Field(value=notes, purpose="NOTES")
            ],
        )
        created_item = self.client.create_item(self.vault_id, new_item)
        return created_item

    def delete_item(self, item_id):
        return self.client.delete_item(self.vault_id, item_id)
    
    def get_item(self, item_id):
        item = self.client.get_item(item_id, self.vault_id)
        return item
    
    def get_item_by_title(self, title: str='', totp: bool=False):
        '''通过title获取具体的值, 会返回一个字典'''
        value = {}
            
        item = self.client.get_item_by_title(title, self.vault_id)

        if totp:
            for field in item.fields:
                if field.totp != None:
                    return field.totp
        else:
            for field in item.fields:
                value[field.label] = field.value
            return value

    def update_item(self, item_id: str, name: str=None, username: str=None, password: str=None, tags: list=None, notes: str=None):
        '''
        更新单个item
        Parms:
            title(str): 一条数据的名称
            name(str): 需要更新的参数值, 例如 username, password
            value(str): 新的值
        Returns:
            Item object(class): 更新后的item
        '''
        # self.get_item_by_title(title="")
        update_item = self.get_item(item_id=item_id)
        
        if name:
            update_item.title = name
        
        for field in update_item.fields:
            if field.purpose == "USERNAME":
                field.value = username
            if field.purpose == "PASSWORD":
                field.value = password
            if field.purpose == "NOTES":
                field.value = notes
        
        if tags:
            update_item.tags = tags
        return self.client.update_item(item_id, self.vault_id, update_item)

    def search_item(self, title: str=None, tag: str=None) -> list:
        if title:
            filter_query = f'title eq "{title}"'
        if tag:
            filter_query = f'tag eq "{tag}"'
        else:
            filter_query = None
        return self.client.get_items(self.vault_id, filter_query=filter_query)


    
if __name__ == "__main__":
    pass
    # my1p.update_item(title='fengmao-server', name='password', value='test')