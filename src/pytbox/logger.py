#!/usr/bin/env python3

import sys
from loguru import logger
from .victorialog import Victorialog


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
                 enable_sls: bool=False,
                 sls_url: str=None,
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
    
    def info(self, message: str='', feishu_notify: bool=False):
        """记录信息级别日志"""
        caller_filename, caller_lineno, caller_function, call_full_filename = self._get_caller_info()
        logger.info(f"[{caller_filename}:{caller_lineno}:{caller_function}] {message}")
        if self.enable_victorialog:
            r = self.victorialog.send_program_log(stream=self.stream, level="INFO", message=message, app_name=self.app_name, file_name=call_full_filename, line_number=caller_lineno, function_name=caller_function)
            print(r)
        if feishu_notify:
            self.feishu(message)
    
    def warning(self, message: str):
        """记录警告级别日志"""
        caller_filename, caller_lineno, caller_function, call_full_filename = self._get_caller_info()
        logger.warning(f"[{caller_filename}:{caller_lineno}:{caller_function}] {message}")
        if self.enable_victorialog:
            self.victorialog.send_program_log(stream=self.stream, level="WARN", message=message, app_name=self.app_name, file_name=call_full_filename, line_number=caller_lineno, function_name=caller_function)
    
    def error(self, message: str):
        """记录错误级别日志"""
        caller_filename, caller_lineno, caller_function, call_full_filename = self._get_caller_info()
        logger.error(f"[{caller_filename}:{caller_lineno}:{caller_function}] {message}")
        if self.enable_victorialog:
            self.victorialog.send_program_log(stream=self.stream, level="ERROR", message=message, app_name=self.app_name, file_name=call_full_filename, line_number=caller_lineno, function_name=caller_function)
        from src.library.monitor.insert_program import insert_error_message
        # 传递清理后的消息给监控系统
        message.replace('#', '')
        insert_error_message(message, self.app_name, caller_filename, caller_lineno, caller_function)
        
    def critical(self, message: str):
        """记录严重错误级别日志"""
        caller_filename, caller_lineno, caller_function, call_full_filename = self._get_caller_info()
        logger.critical(f"[{caller_filename}:{caller_lineno}:{caller_function}] {message}")
        if self.enable_victorialog:
            self.victorialog.send_program_log(stream=self.stream, level="CRITICAL", message=message, app_name=self.app_name, file_name=call_full_filename, line_number=caller_lineno, function_name=caller_function)


def get_logger(app_name: str, enable_) -> AppLogger:
    """
    获取应用日志记录器实例
    
    Args:
        app_name: 应用名称
        log_level: 日志级别
        enable_influx: 是否启用InfluxDB记录
    
    Returns:
        AppLogger: 日志记录器实例
    """
    return AppLogger(app_name)


# 使用示例
if __name__ == "__main__":
    log = get_logger(app_name='test')
    log.info("That's it, beautiful and simple logging!")
    log.warning("That's it, beautiful and simple logging!")
    log.error("That's it, beautiful and simple logging!11")