#!/usr/bin/env python3


from dataclasses import dataclass

@dataclass
class MailDetail:
    """
    邮件详情数据类。
    
    Attributes:
        uid: 邮件唯一标识符
        send_from: 发件人邮箱地址
        send_to: 收件人邮箱地址列表
        cc: 抄送人邮箱地址列表
        subject: 邮件主题
        body_plain: 纯文本正文
        body_html: HTML格式正文
        attachment: 附件完整保存路径列表
    """
    uid: str=None
    sent_from: str=None
    sent_to: list=None
    date: str=None
    cc: list=None
    subject: str=None
    body_plain: str=None
    body_html: str=None
    attachment: list=None
    has_attachments: bool=False