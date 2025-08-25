#!/usr/bin/env python3


from dataclasses import dataclass
from typing import Generator, Literal

import yagmail
from imbox import Imbox
from imap_tools import MailBox, AND, MailMessageFlags
from nb_log import get_logger

from src.library.onepassword import my1p


log = get_logger('src.library.mail.client')


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
    send_from: str=None
    send_to: list=None
    date: str=None
    cc: list=None
    subject: str=None
    body_plain: str=None
    body_html: str=None
    attachment: list=None
    has_attachments: bool=False


class MailClient:
    '''
    _summary_
    '''
    def __init__(self, 
                 send_mail_address: Literal['service@tyun.cn', 'alert@tyun.cn', 'houmingming@tyun.cn', 'houmdream@163.com', 'houm01@foxmail.com'] = 'service@tyun.cn',
                 authorization_code: bool=False,
                 password: str=None
                ):
        
        self.mail_address = send_mail_address
        
        if password:
            self.password = password
        else:
            if authorization_code:
                self.password = my1p.get_item_by_title(title=send_mail_address)['授权码']
            else:
                self.password = my1p.get_item_by_title(title=send_mail_address)['password']

        if '163.com' in send_mail_address:
            self.smtp_address = 'smtp.163.com'
            self.imap_address = 'imap.163.com'
            self.imbox_client = self._create_imbox_object(vendor='163')
        elif 'foxmail.com' in send_mail_address:
            self.smtp_address = 'smtp.qq.com'
            self.imap_address = 'imap.qq.com'
            self.imbox_client = self._create_imbox_object(vendor='qq')
        else:
            raise ValueError(f'不支持的邮箱地址: {send_mail_address}')

        self.mailbox = MailBox(self.imap_address).login(self.mail_address, self.password)
        
    def _create_imbox_object(self, vendor: Literal['aliyun', 'qq', '163']):
        return Imbox(self.imap_address,
                username=self.mail_address,
                password=self.password,
                ssl=True,
                ssl_context=None,
                starttls=False)

    def send_mail(self, receiver: list=[], cc: list=['houmingming@tyun.cn'], subject: str='', contents: str='', attachments: list=[], tips: str=None):
        '''
        _summary_

        Args:
            receiver (list, optional): _description_. Defaults to [].
            cc (list, optional): _description_. Defaults to ['houmingming@tyun.cn'].
            subject (str, optional): _description_. Defaults to ''.
            contents (str, optional): _description_. Defaults to ''.
            attachments (list, optional): _description_. Defaults to [].
        '''
        email_signature = """
————————————————————————————————————————
以专业成就客户 
钛信（上海）信息科技有限公司
Tai Xin（ShangHai) Information Technology Co.,Ltd.
中国上海市浦东新区达尔文路88号半岛科技园21栋2楼
Tel:400-920-0057
Web:www.tyun.cn
————————————————————————————————————————
信息安全声明：本邮件包含信息归发件人所在组织所有，发件人所在组织对该邮件拥有所有权利。请接收者注意保密，未经发件人书面许可，不得向任何第三方组织和个人透露本邮件所含信息的全部或部分。以上声明仅适用于工作邮件。
Information Security Notice: The information contained in this mail is solely property of the sender's organization. This mail communication is confidential. Recipients named above are obligated to maintain secrecy and are not permitted to disclose the contents of this communication to others.
""" 
        with yagmail.SMTP(user=self.mail_address, password=my1p.get_item_by_title(self.mail_address)['password'], port=465, host=self.smtp_address) as yag:
            log.info(f'receiver: {receiver}, cc: {cc}, subject: {subject}, contents: {contents}, attachments: {attachments}')
            try:
                if tips:
                    contents = contents + '\n' + '<p style="color: red;">本邮件为系统自动发送, 如有问题, 请联系 houmingming@tyun.cn</p>'

                contents = contents + email_signature
                yag.send(to=receiver, cc=cc, subject=subject, contents=contents, attachments=attachments)
                log.info('发送成功!!!')
                return True
            except Exception as e:
                log.error(f'发送失败, 报错: {e}')
                return False

    def get_mail_list(self, is_read: bool=False) -> Generator:
        with MailBox(self.imap_address).login(self.mail_address, self.password) as mailbox:
            for msg in mailbox.fetch(criteria=AND(seen=is_read)):
                # 处理附件
                attachment_list = []
                for att in msg.attachments:
                    att_dict = {}
                    att_dict['filename'] = att.filename
                    att_dict['payload'] = att.payload
                    att_dict['size'] = att.size
                    att_dict['content_id'] = att.content_id
                    att_dict['content_type'] = att.content_type
                    att_dict['content_disposition'] = att.content_disposition
                    # att_dict['part'] = att.part
                    att_dict['size'] = att.size
                    attachment_list.append(att_dict)
                
                if attachment_list:
                    is_has_attachments = True
                else:
                    is_has_attachments = False

                yield MailDetail(
                    uid=msg.uid,
                    send_from=msg.from_,
                    send_to=msg.to,
                    date=msg.date,
                    cc=msg.cc,
                    subject=msg.subject,
                    body_plain=msg.text,
                    body_html=msg.html,
                    has_attachments=is_has_attachments,
                    attachment=attachment_list
                )

    def mark_as_read(self, uid):
        """
        标记邮件为已读。
        
        Args:
            uid (str): 邮件的唯一标识符
        """
        try:
            # 使用 imap_tools 的 flag 方法标记邮件为已读
            # 第一个参数是 uid，第二个参数是要设置的标志，第三个参数 True 表示添加标志
            self.mailbox.flag(uid, [MailMessageFlags.SEEN], True)
            # log.info(f'标注邮件{uid}为已读')
        except Exception as e:
            log.error(f'标记邮件{uid}为已读失败: {e}')
            raise
    
    def delete(self, uid):
        """
        删除邮件。
        
        Args:
            uid (str): 邮件的唯一标识符
        """
        try:
            # 使用 imap_tools 的 delete 方法删除邮件
            self.mailbox.delete(uid)
            log.info(f'删除邮件{uid}')
        except Exception as e:
            log.error(f'删除邮件{uid}失败: {e}')
            raise
    
    def move(self, uid: str, destination_folder: str) -> None:
        """
        移动邮件到指定文件夹。

        注意：部分 IMAP 服务商（如 QQ 邮箱）在移动邮件时，实际上是"复制到目标文件夹并从原文件夹删除"，
        这会导致邮件在原文件夹中消失，表现为"被删除"。但邮件会在目标文件夹中存在，并未彻底丢失。

        Args:
            uid (str): 邮件的唯一标识符。
            destination_folder (str): 目标文件夹名称。

        Returns:
            None

        Raises:
            Exception: 移动过程中底层 imap 库抛出的异常。
        """
        try:
            # 使用 imap_tools 的 move 方法移动邮件
            self.mailbox.move(uid, destination_folder)
            log.info(f'邮件{uid}已移动到{destination_folder}')
        except Exception as e:
            log.error(f'移动邮件{uid}到{destination_folder}失败: {e}')
            raise

if __name__ == '__main__':
    # ali_mail = MailClient(send_mail_address='houmingming@tyun.cn')
    # mail = MailClient(send_mail_address='houmingming@tyun.cn')
    # mail = MailClient(send_mail_address='houmdream@163.com', authorization_code=True)
    # mail = MailClient(send_mail_address='houm01@foxmail.com', password=my1p.get_item_by_title('QQ'))
    # 对于阿里云邮箱，使用兼容方法
    pass
    # mail.get_mail_list(attachment=True, attachment_path='/tmp')