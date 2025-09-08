#!/usr/bin/env python3

import time
from functools import wraps
from typing import Literal
from ..database.victoriametrics import VictoriaMetrics


def cronjob_counter(vm: VictoriaMetrics=None, log: str=None, app_type: Literal['']='', app='', comment=None, schedule_interval=None, schedule_cron=None):
    """计算函数运行时间的装饰器，支持记录到 VictoriaMetrics
    
    Args:
        app_type: 应用类型 ('alert', 'meraki', 'other')
        app: 应用名称
        comment: 备注信息
        schedule_interval: 定时任务间隔（如 '1m', '5m'）
        schedule_cron: cron 表达式（如 '0 */5 * * *'）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                elapsed_time = end_time - start_time
                
                # 记录任务成功完成状态
                vm.insert_cronjob_run_status(
                    app_type=app_type,
                    app=app,
                    status_code=1,  # 0 表示成功完成
                    comment=f"成功完成: {comment}" if comment else "任务成功完成",
                    schedule_interval=schedule_interval,
                    schedule_cron=schedule_cron
                )
                
                # 记录执行耗时
                vm.insert_cronjob_duration_seconds(
                    app_type=app_type,
                    app=app,
                    duration_seconds=elapsed_time,
                    comment=comment,
                    schedule_interval=schedule_interval,
                    schedule_cron=schedule_cron
                )
                log.info(f"{app} 任务成功完成, 耗时 {elapsed_time:.2f} 秒")
                
                return result
                
            except Exception as e:
                end_time = time.time()
                elapsed_time = end_time - start_time
                
                # 记录任务失败状态
                error_comment = f"执行出错: {str(e)}" if not comment else f"{comment} (出错: {str(e)})"
                vm.insert_cronjob_run_status(
                    app_type=app_type,
                    app=app,
                    status_code=0,  # 1 表示失败
                    comment=error_comment,
                    schedule_interval=schedule_interval,
                    schedule_cron=schedule_cron
                )
                
                # 即使出错也记录耗时
                vm.insert_cronjob_duration_seconds(
                    app_type=app_type,
                    app=app,
                    duration_seconds=elapsed_time,
                    comment=error_comment,
                    schedule_interval=schedule_interval,
                    schedule_cron=schedule_cron
                )
                log.error(f"任务失败: {error_comment}")
                raise
        return wrapper
    return decorator