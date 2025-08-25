#!/usr/bin/env python3

from typing import Literal
from datetime import datetime, timedelta

import requests



class AliMail:
    def __init__(self, email_address: str=None, client_id: str=None, client_secret: str=None):
        
        self.email_address = email_address
        self.client_id = auth['username']
        self.client_secret = auth['password']
        self.base_url = "https://alimail-cn.aliyuncs.com/v2"
        self.headers = {
                "Content-Type": "application/json",
                "Authorization": f"bearer {self._get_access_token()}"
            }
        
    def _get_access_token(self):
        current_time = datetime.now()
        # stored_token = mongo_alimail_token.find_one({"token_type": "bearer"})
        if stored_token and stored_token.get('expiration_time'):
            expiration_time = stored_token['expiration_time']
            if current_time < expiration_time:
                return stored_token['access_token']
            else:
                return self._get_access_token_by_request()
        else:
            return self._get_access_token_by_request()
    
    def _get_access_token_by_request(self):
        '''
        https://mailhelp.aliyun.com/openapi/index.html#/markdown/authorization.md

        Raises:
            ValueError: _description_

        Returns:
            _type_: _description_
        '''
        # 定义接口URL
        interface_url = "https://alimail-cn.aliyuncs.com/oauth2/v2.0/token"
        # 设置请求头，指定内容类型
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        # 准备请求数据
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        try:
            response = requests.post(interface_url, headers=headers, data=data, timeout=3)
            response_json = response.json()
            current_time = datetime.now()
            data = {
                'token_type': response_json["token_type"],
                'access_token': response_json["access_token"],
                'expires_in':  response_json["expires_in"],
                'expiration_time': current_time + timedelta(seconds=response_json["expires_in"])
            }
            mongo_alimail_token.update_one(
                {"token_type": "bearer"},
                {"$set": data},
                upsert=True
            )
            return data.get("access_token")
        except requests.RequestException as e:
            # 处理请求失败异常
            print(f"请求失败：{e}")
        except (KeyError, ValueError) as e:
            # 处理解析响应失败异常
            print(f"解析响应失败： {e}")

    def list_mail_folders(self):
        response = requests.get(
            url=f"{self.base_url}/users/{self.email_address}/mailFolders",
            headers=self.headers
        )
        return response.json().get('folders')

    def query_folder_id(self, folder_name: Literal['inbox']='inbox'):
        folders = self.list_mail_folders()
        for folder in folders:
            if folder.get('displayName') == folder_name:
                return folder.get('id')
        return None

    def get_mail_detail(self, mail_id: str):
        params = {
            "$select": "body,toRecipients,internetMessageId,internetMessageHeaders"
        }
        response = requests.get(
            url=f"{self.base_url}/users/{self.email_address}/messages/{mail_id}",
            headers=self.headers,
            params=params,
            timeout=3
        )
        return response.json().get('message')

    def list_mail(self, folder_name: str='inbox', size: int=100):
        folder_id = self.query_folder_id(folder_name=folder_name)
        params = {
            "size": size,
            # "$select": "toRecipients"
        }
        response = requests.get(
            url=f"{self.base_url}/users/{self.email_address}/mailFolders/{folder_id}/messages",
            headers=self.headers,
            params=params,
            timeout=3
        )
        messages = response.json().get("messages")
        for message in messages:
            mail_id = message.get("id")
            detail = self.get_mail_detail(mail_id=mail_id)
            message.update(detail)
            yield message
        

if __name__ == '__main__':
    ali_mail = AliMail()
    # print(ali_mail.query_folder_id())
    # for i in ali_mail.list_mail(size=1):
    #     print(i)
    # print(ali_mail.access_token)
    print(ali_mail.get_mail_detail(mail_id='DzzzzzzMeuY'))