#!/usr/bin/env python3


import time


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