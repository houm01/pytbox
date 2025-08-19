#!/usr/bin/env python3


import time
import pytz
import datetime
from typing import Literal


class TimeUtils:
    
    @staticmethod
    def get_timestamp(now: bool=True) -> int:
        '''
        获取时间戳
        
        Args:
            now (bool, optional): _description_. Defaults to True.

        Returns:
            _type_: _description_
        '''
        if now:
            return int(time.time())
        else:
            return int(time.time() * 1000)
    
    @staticmethod
    def get_time_object(now: bool=True):
        '''
        获取当前时间, 加入了时区信息, 简单是存储在 Mongo 中时格式为 ISODate

        Returns:
            current_time(class): 时间, 格式: 2024-04-23 16:48:11.591589+08:00
        '''
        if now:
            return datetime.datetime.now(pytz.timezone('Asia/Shanghai'))
    
    @staticmethod
    def get_utc_time():
        return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    
    @staticmethod
    def get_now_time_mongo():
        return datetime.datetime.now(pytz.timezone('Asia/Shanghai'))

    @staticmethod
    def convert_timeobj_to_str(timeobj: str=None, timezone_offset: int=8, time_format: Literal['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%SZ']='%Y-%m-%d %H:%M:%S'):
        time_obj_with_offset = timeobj + datetime.timedelta(hours=timezone_offset)
        if time_format == '%Y-%m-%d %H:%M:%S':
            return time_obj_with_offset.strftime("%Y-%m-%d %H:%M:%S")
        elif time_format == '%Y-%m-%dT%H:%M:%SZ':
            return time_obj_with_offset.strftime("%Y-%m-%dT%H:%M:%SZ")