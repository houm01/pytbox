#!/usr/bin/env python3

import re
import pytz
import time
import datetime
from zoneinfo import ZoneInfo
from typing import Literal


class TimeUtils:
    
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

    @staticmethod
    def get_time_diff_hours(time1, time2):
        """
        计算两个datetime对象之间的小时差
        
        Args:
            time1: 第一个datetime对象
            time2: 第二个datetime对象
            
        Returns:
            float: 两个时间之间的小时差
        """
        if not time1 or not time2:
            return 0
        
        # 确保两个时间都有时区信息
        if time1.tzinfo is None:
            time1 = time1.replace(tzinfo=pytz.timezone('Asia/Shanghai'))
        if time2.tzinfo is None:
            time2 = time2.replace(tzinfo=pytz.timezone('Asia/Shanghai'))
        
        # 计算时间差（秒）
        time_diff_seconds = abs((time2 - time1).total_seconds())
        
        # 转换为小时
        time_diff_hours = time_diff_seconds / 3600
        
        return time_diff_hours

    @staticmethod
    def convert_syslog_huawei_str_to_8601(timestr):
        """
        将华为 syslog 格式的时间字符串（如 '2025-08-02T04:34:24+08:00'）转换为 ISO8601 格式的 UTC 时间字符串。

        Args:
            timestr (str): 原始时间字符串，格式如 '2025-08-02T04:34:24+08:00'

        Returns:
            str: 转换后的 ISO8601 格式 UTC 时间字符串，如 '2025-08-01T20:34:24.000000Z'
        """
        if timestr is None:
            return None
        try:
            # 解析带时区的时间字符串
            dt: datetime.datetime = datetime.datetime.strptime(timestr, "%Y-%m-%dT%H:%M:%S%z")
            # 转换为 UTC
            dt_utc: datetime.datetime = dt.astimezone(datetime.timezone.utc)
            # 格式化为 ISO8601 字符串（带微秒，Z 结尾）
            iso8601_utc: str = dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            return iso8601_utc
        except ValueError as e:
            # 日志记录异常（此处仅简单打印，实际项目建议用 logging）
            print(f"时间转换失败: {e}, 输入: {timestr}")
            return None
     
    @staticmethod
    def convert_str_to_timestamp(timestr):
        """
        将类似 '2025-04-16T00:08:28.000+0000' 格式的时间字符串转换为时间戳（秒级）。

        Args:
            timestr (str): 时间字符串，格式如 '2025-04-16T00:08:28.000+0000'

        Returns:
            int: 时间戳（秒级）
        """
        if timestr is None:
            return None
        # 兼容带毫秒和时区的ISO8601格式
        # 先将+0000或+08:00等时区格式标准化为+00:00
        timestr_fixed = re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', timestr)
   
        # 处理毫秒部分（.000），如果没有毫秒也能兼容
        try:
            dt = datetime.datetime.fromisoformat(timestr_fixed)
        except ValueError:
            if len(timestr_fixed) == 8:
                dt = datetime.datetime.strptime(timestr_fixed, "%Y%m%d")
            else:
                # 如果没有毫秒部分
                dt = datetime.datetime.strptime(timestr_fixed, "%Y-%m-%dT%H:%M:%S%z")
        # 返回秒级时间戳
        return int(dt.timestamp()) * 1000
    
    @staticmethod
    def convert_str_to_datetime_lg_backup(time_str: str):
        """
        将 '7/10/2025 3:52:43 PM' 这种格式的时间字符串转换为时间戳（秒级）。

        Args:
            time_str (str): 时间字符串，格式如 '7/10/2025 3:52:43 PM'

        Returns:
            int: 时间戳（秒级）
        """
        if time_str is None:
            return None
        # 先将字符串转换为 datetime 对象
        dt = datetime.datetime.strptime(time_str, "%m/%d/%Y %I:%M:%S %p")
        # 返回秒级时间戳
        return int(dt.timestamp()) * 1000
        
    @staticmethod
    def convert_timestamp_to_str(timestamp: int, time_format: Literal['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S.000Z']='%Y-%m-%d %H:%M:%S', timezone_offset: int=8):
        '''
        _summary_

        Args:
            timestamp (_type_): _description_

        Returns:
            _type_: _description_
        '''
        timestamp = int(timestamp)
        if timestamp > 10000000000:
            timestamp = timestamp / 1000
        # 使用datetime模块的fromtimestamp方法将时间戳转换为datetime对象
        dt_object = datetime.datetime.fromtimestamp(timestamp, tz=ZoneInfo(f'Etc/GMT-{timezone_offset}'))

        # 使用strftime方法将datetime对象格式化为字符串
        return dt_object.strftime(time_format)

    @staticmethod
    def timestamp_to_timestr_dida(timestamp):
        # 将时间戳转换为 UTC 时间
        utc_time = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)

        # 将 UTC 时间转换为指定时区（+08:00）
        target_timezone = datetime.timezone(datetime.timedelta(hours=8))
        local_time = utc_time.astimezone(target_timezone)

        # 格式化为指定字符串
        formatted_time = local_time.strftime('%Y-%m-%dT%H:%M:%S%z')

        # 添加冒号到时区部分
        formatted_time = formatted_time[:-2] + ':' + formatted_time[-2:]
        return formatted_time
        
    @staticmethod
    def timestamp_to_datetime_obj(timestamp: int, timezone_offset: int=8):
        return datetime.datetime.fromtimestamp(timestamp, tz=ZoneInfo(f'Etc/GMT-{timezone_offset}'))

    @staticmethod
    def datetime_obj_to_str(datetime_obj, add_timezone=False):
        if add_timezone:
            datetime_obj = datetime_obj.astimezone(pytz.timezone('Asia/Shanghai'))
        return datetime_obj.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def get_current_time(app: Literal['notion', 'dida365']):
        if app == 'notion':
            return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        elif app == 'dida365':
            return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S%z")

    @staticmethod
    def get_current_date_str(output_format: Literal['%Y%m%d', '%Y-%m-%d']='%Y%m%d') -> str:
        # 获取当前日期和时间
        now = datetime.datetime.now()

        # 格式化为字符串
        current_date_str = now.strftime(output_format)
        return current_date_str
    
    @staticmethod
    def get_date_n_days_from_now(n: int = 0, output_format: Literal['%Y%m%d', '%Y-%m-%d'] = '%Y%m%d') -> str:
        """
        获取距离当前日期 N 天后的日期字符串。

        Args:
            n (int): 天数，可以为负数（表示 N 天前），默认为 0（即今天）。
            output_format (Literal['%Y%m%d', '%Y-%m-%d']): 日期输出格式，默认为 '%Y%m%d'。

        Returns:
            str: 格式化后的日期字符串。

        示例:
            >>> MyTime.get_date_n_days_from_now(1)
            '20240620'
            >>> MyTime.get_date_n_days_from_now(-1, '%Y-%m-%d')
            '2024-06-18'
        """
        target_date = datetime.datetime.now() + datetime.timedelta(days=n)
        return target_date.strftime(output_format)
    
    
    @staticmethod
    def get_yesterday_date_str() -> str:
        # 获取昨天日期
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        yesterday_date_str = yesterday.strftime("%Y%m%d")
        return yesterday_date_str

    @staticmethod
    def get_last_month_date_str() -> str:
        # 获取上个月日期
        last_month = datetime.datetime.now() - datetime.timedelta(days=30)
        last_month_date_str = last_month.strftime("%Y-%m")
        return last_month_date_str
    
    @staticmethod
    def get_current_time_str() -> str:
        # 获取当前日期和时间
        now = datetime.datetime.now()

        # 格式化为字符串
        current_date_str = now.strftime("%Y%m%d_%H%M")
        return current_date_str
    
    @staticmethod
    def get_timestamp(now: bool=True, last_minutes: int=0, unit: Literal['ms', 's']='ms') -> int:
        '''
        获取当前时间戳, 减去 last_minutes 分钟
        ''' 
        if now:
            if unit == 'ms':
                return int(time.time()) * 1000
            elif unit == 's':
                return int(time.time())
        
        if last_minutes == 0:
            if unit == 'ms':
                return int(time.time()) * 1000
            elif unit == 's':
                return int(time.time())
        else:
            if unit == 'ms':
                return int(time.time()) * 1000 - last_minutes * 60 * 1000
            elif unit == 's':
                return int(time.time()) - last_minutes * 60
            
    @staticmethod
    def get_timestamp_tomorrow() -> int:
        return int(time.time()) * 1000 + 24 * 60 * 60 * 1000
    
    @staticmethod
    def get_timestamp_last_day(last_days: int=0, unit: Literal['ms', 's']='ms') -> int:
        if last_days == 0:
            if unit == 'ms':
                return int(time.time()) * 1000
            elif unit == 's':
                return int(time.time())
        else:
            return int(time.time()) * 1000 - last_days * 24 * 60 * 60 * 1000
    
    @staticmethod
    def get_today_timestamp() -> int:
        return int(time.time()) * 1000

    @staticmethod
    def convert_str_to_datetime(time_str: str, app: Literal['lg_alert_trigger', 'lg_alert_resolved', 'mongo']='lg_alert_trigger') -> datetime.datetime:
        """
        将字符串转换为datetime对象

        Args:
            time_str (str): 时间字符串
            app (Literal['lg_alert_trigger', 'lg_alert_resolved', 'mongo'], optional): 应用类型. Defaults to 'lg_alert_trigger'.

        Returns:
            datetime.datetime: 带时区信息的datetime对象
        """
        if app == 'lg_alert_trigger':
            time_obj = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        elif app == 'lg_alert_resolved':
            time_obj = datetime.datetime.strptime(time_str, "%Y年%m月%d日 %H:%M:%S")
        elif app == 'mongo':
            time_obj = datetime.datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return time_obj  # 已经包含时区信息，直接返回
        
        # 对于没有时区信息的时间对象，设置为Asia/Shanghai时区
        time_with_tz = time_obj.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
        return time_with_tz

    @staticmethod
    def convert_timeobj_to_str(timeobj: str=None, timezone_offset: int=8, time_format: Literal['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%SZ']='%Y-%m-%d %H:%M:%S'):
        time_obj_with_offset = timeobj + datetime.timedelta(hours=timezone_offset)
        if time_format == '%Y-%m-%d %H:%M:%S':
            return time_obj_with_offset.strftime("%Y-%m-%d %H:%M:%S")
        elif time_format == '%Y-%m-%dT%H:%M:%SZ':
            return time_obj_with_offset.strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def convert_timestamp_to_timeobj(timestamp: int) -> datetime.datetime:
        """
        将时间戳转换为时间对象

        Args:
            timestamp (int): 时间戳，单位为秒或毫秒

        Returns:
            datetime.datetime: 转换后的时间对象，时区为 Asia/Shanghai
        """
        # 如果时间戳是毫秒，转换为秒
        if len(str(timestamp)) > 10:
            timestamp = timestamp / 1000
        
        return datetime.datetime.fromtimestamp(timestamp, tz=ZoneInfo("Asia/Shanghai"))

    @staticmethod
    def convert_timeobj_to_timestamp(timeobj: datetime.datetime) -> int:
        """
        将时间对象转换为时间戳

        Args:
            timeobj (datetime.datetime): 时间对象

        Returns:
            int: 时间戳，单位为秒或毫秒
        """
        return int(timeobj.timestamp())

    @staticmethod
    def convert_timeobj_add_timezone(timeobj: datetime.datetime, timezone_offset: int=8) -> datetime.datetime:
        return timeobj + datetime.timedelta(hours=timezone_offset)

    @staticmethod
    def convert_mute_duration(mute_duration: str) -> datetime.datetime:
        """将屏蔽时长字符串转换为带 Asia/Shanghai 时区的 ``datetime`` 对象。

        支持两类输入：
        - 绝对时间: 例如 ``"2025-01-02 13:45"``，按本地上海时区解释。
        - 相对时间: 形如 ``"10m"``、``"2h"``、``"1d"`` 分别表示分钟、小时、天。

        Args:
            mute_duration: 屏蔽时长字符串。

        Returns:
            datetime.datetime: 带 ``Asia/Shanghai`` 时区信息的时间点。

        Raises:
            ValueError: 当输入字符串无法被解析时抛出。
        """
        shanghai_tz = ZoneInfo("Asia/Shanghai")
        now: datetime.datetime = datetime.datetime.now(tz=shanghai_tz)
        mute_duration = mute_duration.strip()

        # 绝对时间格式（按上海时区解释）
        try:
            abs_dt_naive = datetime.datetime.strptime(mute_duration, "%Y-%m-%d %H:%M")
            return abs_dt_naive.replace(tzinfo=shanghai_tz)
        except ValueError:
            pass

        # 相对时间格式
        pattern = r"^(\d+)([dhm])$"
        match = re.match(pattern, mute_duration)
        if match:
            value_str, unit = match.groups()
            value = int(value_str)
            if unit == "d":
                return now + datetime.timedelta(days=value)
            if unit == "h":
                return now + datetime.timedelta(hours=value)
            if unit == "m":
                return now + datetime.timedelta(minutes=value)

        raise ValueError(f"无法解析 mute_duration: {mute_duration}")

    @staticmethod
    def convert_mute_duration_to_str(mute_duration: str) -> str:
        '''
        将屏蔽时长字符串转换为距离当前时间的标准描述，形如 '2d3h'。

        支持两类输入：
        - 绝对时间: 'YYYY-MM-DD HH:MM'（按 Asia/Shanghai 解释）
        - 相对时间: '10m'、'2h'、'1d'

        如果目标时间已过去，则返回 '0h'。

        Args:
            mute_duration (str): 屏蔽时长字符串。

        Returns:
            str: 与当前时间的距离描述，例如 '1d2h'、'3h'。
        '''
        shanghai_tz = ZoneInfo("Asia/Shanghai")
        now: datetime.datetime = datetime.datetime.now(tz=shanghai_tz)

        try:
            target_time: datetime.datetime = TimeUtils.convert_mute_duration(mute_duration)
        except ValueError:
            # 兜底：直接尝试绝对时间格式
            try:
                abs_dt = datetime.datetime.strptime(mute_duration.strip(), "%Y-%m-%d %H:%M")
                target_time = abs_dt.replace(tzinfo=shanghai_tz)
            except ValueError:
                return mute_duration

        # 计算与现在的差值（仅面向未来的剩余时长）
        delta_seconds: float = (target_time - now).total_seconds()
        if delta_seconds <= 0:
            return "0h"

        days: int = int(delta_seconds // 86400)
        hours: int = int((delta_seconds % 86400) // 3600)

        parts: list[str] = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if not parts:
            # 小于 1 小时
            parts.append("0h")

        return "".join(parts)

    @staticmethod
    def is_work_time(start_hour: int=9, end_hour: int=18) -> bool:
        '''
        判断是否为工作时间

        Args:
            start_hour (int, optional): 开始工作时间. Defaults to 9.
            end_hour (int, optional): 结束工作时间. Defaults to 18.

        Returns:
            bool: 如果是工作时间, 返回 True, 否则返回 False
        '''
        current_time = datetime.datetime.now().time()
        start = datetime.time(start_hour, 0, 0)
        end = datetime.time(end_hour, 0, 0)
        
        if start <= current_time <= end:
            return True
        else:
            return False
    
    @staticmethod
    def is_work_day() -> bool:
        '''
        判断是否为工作日

        Returns:
            bool: 如果是工作日, 返回 True, 否则返回 False
        '''
        from chinese_calendar import is_workday
        date_now = datetime.datetime.date(datetime.datetime.now())
        # print(date_now)
        if is_workday(date_now):
            return True
        else:
            return False
        
    @staticmethod
    def get_week_number(offset: int=5) -> int:
        '''
        获取今天是哪一年的第几周
        
        Returns:
            int: 返回一个元组，包含(年份, 周数)
        '''
        now = datetime.datetime.now()
        # isocalendar()方法返回一个元组，包含年份、周数和周几
        _year_unused, week, _ = now.isocalendar()
        return week - offset
    
    @staticmethod
    def get_week_day(timestamp: int=None, offset: int=0) -> int:
        '''
        获取今天是周几
        
        Returns:
            int: 周几的数字表示，1表示周一，7表示周日
        '''
        if timestamp is None:
            now = datetime.datetime.now()
        else:
            if timestamp > 10000000000:
                timestamp = timestamp / 1000
            now = datetime.datetime.fromtimestamp(timestamp)
        # weekday()方法返回0-6的数字，0表示周一，6表示周日
        return now.weekday() + 1 + offset
    
    @staticmethod
    def get_week_of_year(customer: Literal['lululemon', 'other']='other') -> tuple[int, int]:
        '''
        获取今天是哪一年的第几周
        
        Returns:
            tuple[int, int]: 返回一个元组，包含(年份, 周数)
        '''
        now = datetime.datetime.now()
        # isocalendar()方法返回一个元组，包含年份、周数和周几
        _year, week, _ = now.isocalendar()
        if customer == 'lululemon':
            week = week - 5
        return _year, week

    @staticmethod
    def get_last_month_start_and_end_time() -> tuple[datetime.datetime, datetime.datetime]:
        '''
        获取上个月的开始和结束时间

        Returns:
            tuple[datetime.datetime, datetime.datetime]: 返回一个元组，包含上个月的开始和结束时间
        '''
        today = datetime.datetime.now()
        # 获取当前月份的第一天
        first_day_of_current_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # 上个月1号的0:00分
        start_time = first_day_of_current_month - datetime.timedelta(days=1)
        start_time = start_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # 获取上个月的最后一天
        end_time = first_day_of_current_month - datetime.timedelta(days=1)
        end_time = end_time.replace(hour=23, minute=59, second=59, microsecond=0)
        return start_time.strftime("%Y-%m-%dT%H:%M:%SZ"), end_time.strftime("%Y-%m-%dT%H:%M:%SZ")