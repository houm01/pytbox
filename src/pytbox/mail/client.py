#!/usr/bin/env python3


from contextlib import contextmanager
import yagmail
from imap_tools import MailBox, MailMessageFlags, AND
from .mail_detail import MailDetail
from ..utils.response import ReturnResponse


class MailClient:
    '''
    _summary_
    '''
    def __init__(self, 
                 mail_address: str=None,
                 password: str=None
                ):
        
        self.mail_address = mail_address
        self.password = password

        if '163.com' in mail_address:
            self.smtp_address = 'smtp.163.com'
            self.imap_address = 'imap.163.com'
            # self.imbox_client = self._create_imbox_object()
        elif 'foxmail.com' in mail_address:
            self.smtp_address = 'smtp.qq.com'
            self.imap_address = 'imap.qq.com'
        
        elif 'mail' in mail_address and 'cn' in mail_address:
            self.smtp_address = "smtpdm.aliyun.com"
            self.imap_address = ""
            
        else:
            raise ValueError(f'不支持的邮箱地址: {mail_address}')
    
    @contextmanager
    def get_mailbox(self, readonly=False):
        """
        创建并返回一个已登录的 MailBox 上下文管理器。
        
        使用方式:
            with self.get_mailbox() as mailbox:
                # 使用 mailbox 进行操作
                pass
        
        Args:
            readonly (bool): 是否以只读模式打开邮箱，只读模式下不会将邮件标记为已读
        
        Yields:
            MailBox: 已登录的邮箱对象
        """
        mailbox = MailBox(self.imap_address).login(self.mail_address, self.password)
        if readonly:
            # 以只读模式选择收件箱，防止邮件被标记为已读
            mailbox.folder.set('INBOX', readonly=True)
        try:
            yield mailbox
        finally:
            mailbox.logout()

    def send_mail(self, receiver: list=None, cc: list=None, subject: str='', contents: str='', attachments: list=None, tips: str=None):
        '''
        _summary_

        Args:
            receiver (list, optional): _description_. Defaults to None.
            cc (list, optional): _description_. Defaults to None.
            subject (str, optional): _description_. Defaults to ''.
            contents (str, optional): _description_. Defaults to ''.
            attachments (list, optional): _description_. Defaults to None.
        '''
        with yagmail.SMTP(user=self.mail_address, password=self.password, port=465, host=self.smtp_address) as yag:
            try:
                if tips:
                    contents = contents + '\n' + '<p style="color: red;">本邮件为系统自动发送</p>'
                yag.send(to=receiver, cc=cc, subject=subject, contents=contents, attachments=attachments)
                return True
            except Exception as e:
                return False
            
    def get_mail_list(self, seen: bool=False, readonly: bool=True):
        '''
        获取邮件

        Args:
            seen (bool, optional): 默认获取未读邮件, 如果为 True, 则获取已读邮件
            readonly (bool, optional): 是否以只读模式获取邮件，默认为 True，防止邮件被标记为已读

        Yields:
            MailDetail: 邮件详情
        '''
        with self.get_mailbox(readonly=readonly) as mailbox:
            for msg in mailbox.fetch(AND(seen=seen)):
                yield MailDetail(
                    uid=msg.uid,
                    sent_from=msg.from_,
                    sent_to=msg.to,
                    date=msg.date,
                    cc=msg.cc,
                    subject=msg.subject,
                    body_plain=msg.text,
                    body_html=msg.html
                )     
            
    def mark_as_read(self, uid):
        """
        标记邮件为已读。
        
        Args:
            uid (str): 邮件的唯一标识符
        """
        try:
            with self.get_mailbox() as mailbox:
                # 使用 imap_tools 的 flag 方法标记邮件为已读
                # 第一个参数是 uid，第二个参数是要设置的标志，第三个参数 True 表示添加标志
                mailbox.flag(uid, [MailMessageFlags.SEEN], True)
        except Exception as e:
            return ReturnResponse(code=1, msg='邮件删除失败', data=e)
    
    def delete(self, uid):
        """
        删除邮件。
        
        Args:
            uid (str): 邮件的唯一标识符
        """
        try:
            with self.get_mailbox() as mailbox:
                # 使用 imap_tools 的 delete 方法删除邮件
                mailbox.delete(uid)
                # log.info(f'删除邮件{uid}')
        except Exception as e:
            # log.error(f'删除邮件{uid}失败: {e}')
            raise
    
    def move(self, uid: str, destination_folder: str) -> ReturnResponse:
        """
        移动邮件到指定文件夹。

        注意：部分 IMAP 服务商（如 QQ 邮箱）在移动邮件时，实际上是"复制到目标文件夹并从原文件夹删除"，
        这会导致邮件在原文件夹中消失，表现为"被删除"。但邮件会在目标文件夹中存在，并未彻底丢失。

        Args:
            uid (str): 邮件的唯一标识符。
            destination_folder (str): 目标文件夹名称。

        Returns:
            ReturnResponse: 移动邮件结果

        Raises:
            Exception: 移动过程中底层 imap 库抛出的异常。
        """
        try:
            with self.get_mailbox() as mailbox:
                # 使用 imap_tools 的 move 方法移动邮件
                mailbox.move(uid, destination_folder)
                return ReturnResponse(code=0, msg=f'邮件 {uid} 移动到 {destination_folder} 成功', data=None)
        except Exception as e:
            return ReturnResponse(code=1, msg=f'邮件 {uid} 移动到 {destination_folder} 失败', data=e)

    def get_folder_list(self):
        '''
        获取文件夹列表
        '''
        with self.get_mailbox() as mailbox:
            return ReturnResponse(code=0, msg='获取文件夹列表成功', data=mailbox.folder.list())

if __name__ == '__main__':
    pass