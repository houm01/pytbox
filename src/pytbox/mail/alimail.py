#!/usr/bin/env python3

from typing import Literal
from datetime import datetime, timedelta

import requests
from ..utils.response import ReturnResponse
from .mail_detail import MailDetail
from ..utils.timeutils import TimeUtils



class AliMail:
    '''
    _summary_
    '''
    def __init__(self, mail_address: str=None, client_id: str=None, client_secret: str=None, timeout: int=3):
        self.email_address = mail_address
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://alimail-cn.aliyuncs.com/v2"
        self.timeout = timeout
        self.headers = {
                "Content-Type": "application/json",
                "Authorization": f"bearer {self._get_access_token_by_request()}"
            }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    
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
            response = requests.post(interface_url, headers=headers, data=data, timeout=self.timeout)
            response_json = response.json()
            current_time = datetime.now()
            data = {
                'token_type': response_json["token_type"],
                'access_token': response_json["access_token"],
                'expires_in':  response_json["expires_in"],
                'expiration_time': current_time + timedelta(seconds=response_json["expires_in"])
            }
            return data.get("access_token")
        except requests.RequestException as e:
            # 处理请求失败异常
            raise e
        except (KeyError, ValueError) as e:
            # 处理解析响应失败异常
            raise e

    def get_mail_folders(self):
        response = self.session.get(
            url=f"{self.base_url}/users/{self.email_address}/mailFolders",
            headers=self.headers
        )
        return response.json().get('folders')

    def get_folder_id(self, folder_name: Literal['inbox']='inbox'):
        folders = self.get_mail_folders()
        for folder in folders:
            if folder.get('displayName') == folder_name:
                return folder.get('id')
        return None

    def get_mail_detail(self, mail_id: str):
        params = {
            "$select": "body,toRecipients,internetMessageId,internetMessageHeaders"
        }
        response = self.session.get(
            url=f"{self.base_url}/users/{self.email_address}/messages/{mail_id}",
            headers=self.headers,
            params=params,
            timeout=3
        )
        return response.json().get('message')

    def get_mail_list(self, folder_name: str='inbox', size: int=100):
        folder_id = self.get_folder_id(folder_name=folder_name)
        params = {
            "size": size,
            # "$select": "toRecipients"
        }
        response = self.session.get(
            url=f"{self.base_url}/users/{self.email_address}/mailFolders/{folder_id}/messages",
            headers=self.headers,
            params=params,
            timeout=3
        )
        messages = response.json().get("messages")
        sent_to_list = []
        for message in messages:
            mail_id = message.get("id")
            detail = self.get_mail_detail(mail_id=mail_id)
            
            for to_recipient in detail.get('toRecipients'):
                sent_to_list.append(to_recipient.get('email'))
            
            yield MailDetail(
                uid=message.get('id'),
                sent_from=message.get('from').get('email'),
                sent_to=sent_to_list,
                date=TimeUtils.convert_str_to_datetime(time_str=message.get('sentDateTime'), app='alimail'),
                cc="",
                subject=message.get('subject'),
                body_plain=message.get('summary'),
                body_html=""
            )

    def move(self, uid: str, destination_folder: str) -> ReturnResponse:
        params = {
            "ids": [uid],
            "destinationFolderId": self.get_folder_id(destination_folder)
        }
        r = self.session.post(
            url=f"{self.base_url}/users/{self.email_address}/messages/move",
            params=params
        )
        if r.status_code == 200:
            return ReturnResponse(code=0, msg=f'邮件移动到 {destination_folder} 成功', data=None)
        else:
            return ReturnResponse(code=1, msg=f'邮件移动到 {destination_folder} 失败', data=r.json())

if __name__ == '__main__':
    ali_mail = AliMail()