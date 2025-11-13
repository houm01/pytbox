#!/usr/bin/env python3

import sys

from loguru import logger

from .victorialog import Victorialog
from ..database.mongo import Mongo
from ..feishu.client import Client as FeishuClient
from ..utils.timeutils import TimeUtils
from ..dida365 import Dida365
from ..alicloud.sls import AliCloudSls

logger.remove()
logger.add(sys.stdout, colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>")


class AppLogger:
    """
    应用日志记录器类
    
    提供统一的日志记录接口，支持多种日志级别和外部服务集成。
    自动记录调用者信息（文件名、行号、函数名）到日志中。
    """
    def __init__(self, 
                 app_name: str='inbox', 
                 stream: str='automation', 
                 enable_victorialog: bool=False, 
                 victorialog_url: str=None,
                 mongo: Mongo=None,
                 feishu: FeishuClient=None,
                 dida: Dida365=None,
                 enable_sls: bool=False,
                 sls_access_key_id: str=None,
                 sls_access_key_secret: str=None,
                 sls_project: str=None,
                 sls_logstore: str=None,
                 sls_topic: str=None,
            ):
        """
        初始化应用日志记录器
        
        Args:
            app_name: 应用名称，用于标识日志来源
            stream: 日志流名称，用于VictoriaLogs分类
        """
        self.app_name = app_name
        self.stream = stream
        self.victorialog = Victorialog(url=victorialog_url)
        self.enable_victorialog = enable_victorialog
        self.enable_sls = enable_sls
        self.mongo = mongo
        self.feishu = feishu
        self.dida = dida
        self.sls = AliCloudSls(
            access_key_id=sls_access_key_id,
            access_key_secret=sls_access_key_secret,
            project=sls_project,
            logstore=sls_logstore
        )

    def _get_caller_info(self) -> tuple[str, int, str]:
        """
        获取调用者信息
        
        Returns:
            tuple: (文件名, 行号, 函数名)
        """
        import inspect
        stack = inspect.stack()
        caller = stack[2]  # 索引0是当前函数，索引1是_get_caller_info，索引2是实际调用者
        
        # 获取调用者的文件名、行号、函数名
        call_full_filename = caller.filename
        caller_filename = caller.filename.split('/')[-1]
        caller_lineno = caller.lineno
        caller_function = caller.function
        
        return caller_filename, caller_lineno, caller_function, call_full_filename
    
    def debug(self, message: str):
        """记录调试级别日志"""
        caller_filename, caller_lineno, caller_function, call_full_filename = self._get_caller_info()
        logger.debug(f"[{caller_filename}:{caller_lineno}:{caller_function}] {message}")
        if self.enable_victorialog:
            self.victorialog.send_program_log(stream=self.stream, level="DEBUG", message=message, app_name=self.app_name, file_name=call_full_filename, line_number=caller_lineno, function_name=caller_function)
        if self.enable_sls:
            self.sls.put_logs(level="DEBUG", msg=message, app=self.app_name, caller_filename=caller_filename, caller_lineno=caller_lineno, caller_function=caller_function, call_full_filename=call_full_filename)
 
    
    def info(self, message: str='', feishu_notify: bool=False):
        """记录信息级别日志"""
        caller_filename, caller_lineno, caller_function, call_full_filename = self._get_caller_info()
        logger.info(f"[{caller_filename}:{caller_lineno}:{caller_function}] {message}")
        if self.enable_victorialog:
            r = self.victorialog.send_program_log(stream=self.stream, level="INFO", message=message, app_name=self.app_name, file_name=call_full_filename, line_number=caller_lineno, function_name=caller_function)
        if self.enable_sls:
            self.sls.put_logs(level="INFO", msg=message, app=self.app_name, caller_filename=caller_filename, caller_lineno=caller_lineno, caller_function=caller_function, call_full_filename=call_full_filename)
        if feishu_notify:
            self.feishu.extensions.send_message_notify(
                title=f"自动化脚本告警: {self.app_name}",
                content=f"触发时间: {TimeUtils.get_current_time_str()}\n{message}"
            )
        
    def warning(self, message: str):
        """记录警告级别日志"""
        caller_filename, caller_lineno, caller_function, call_full_filename = self._get_caller_info()
        logger.warning(f"[{caller_filename}:{caller_lineno}:{caller_function}] {message}")
        if self.enable_victorialog:
            self.victorialog.send_program_log(stream=self.stream, level="WARN", message=message, app_name=self.app_name, file_name=call_full_filename, line_number=caller_lineno, function_name=caller_function)
        if self.enable_sls:
            self.sls.put_logs(level="WARN", msg=message, app=self.app_name, caller_filename=caller_filename, caller_lineno=caller_lineno, caller_function=caller_function, call_full_filename=call_full_filename)
            
    def error(self, message: str):
        """记录错误级别日志"""
        caller_filename, caller_lineno, caller_function, call_full_filename = self._get_caller_info()
        logger.error(f"[{caller_filename}:{caller_lineno}:{caller_function}] {message}")
        if self.enable_victorialog:
            self.victorialog.send_program_log(stream=self.stream, level="ERROR", message=message, app_name=self.app_name, file_name=call_full_filename, line_number=caller_lineno, function_name=caller_function)
        if self.enable_sls:
            self.sls.put_logs(level="ERROR", msg=message, app=self.app_name, caller_filename=caller_filename, caller_lineno=caller_lineno, caller_function=caller_function, call_full_filename=call_full_filename)
        
        if self.feishu:
            existing_message = self.mongo.collection.find_one({"message": message}, sort=[("time", -1)])
            current_time = TimeUtils.get_now_time_mongo()

            if not existing_message or TimeUtils.get_time_diff_hours(existing_message["time"], current_time) > 36:
                self.mongo.collection.insert_one({
                    "message": message,
                    "time": current_time,
                    "file_name": caller_filename,
                    "line_number": caller_lineno,
                    "function_name": caller_function
                })
                    
                    
                content_list = [
                    f"{self.feishu.extensions.format_rich_text(text='app:', color='blue', bold=True)} {self.app_name}",
                    f"{self.feishu.extensions.format_rich_text(text='message:', color='blue', bold=True)} {message}",
                    f"{self.feishu.extensions.format_rich_text(text='file_name:', color='blue', bold=True)} {caller_filename}",
                    f"{self.feishu.extensions.format_rich_text(text='line_number:', color='blue', bold=True)} {caller_lineno}",
                    f"{self.feishu.extensions.format_rich_text(text='function_name:', color='blue', bold=True)} {caller_function}"
                ]
                
                self.feishu.extensions.send_message_notify(
                    title=f"自动化脚本告警: {self.app_name}",
                    content="\n".join(content_list)
                )
                
                dida_content_list = [
                    f"**app**: {self.app_name}",
                    f"**message**: {message}",
                    f"**file_name**: {caller_filename}",
                    f"**line_number**: {caller_lineno}",
                    f"**function_name**: {caller_function}"
                ]
                
                if self.dida:
                    self.dida.task_create(
                        project_id="65e87d2b3e73517c2cdd9d63",
                        title=f"自动化脚本告警: {self.app_name}",
                        content="\n".join(dida_content_list),
                        tags=['L-程序告警', 't-问题处理']
                    )
        
    def critical(self, message: str):
        """记录严重错误级别日志"""
        caller_filename, caller_lineno, caller_function, call_full_filename = self._get_caller_info()
        logger.critical(f"[{caller_filename}:{caller_lineno}:{caller_function}] {message}")
        if self.enable_victorialog:
            self.victorialog.send_program_log(stream=self.stream, level="CRITICAL", message=message, app_name=self.app_name, file_name=call_full_filename, line_number=caller_lineno, function_name=caller_function)
        if self.enable_sls:
            self.sls.put_logs(level="CRITICAL", msg=message, app=self.app_name, caller_filename=caller_filename, caller_lineno=caller_lineno, caller_function=caller_function, call_full_filename=call_full_filename)

# 使用示例
if __name__ == "__main__":
    pass