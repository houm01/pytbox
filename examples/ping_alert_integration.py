#!/usr/bin/env python3
"""
ping告警集成示例

展示如何将简单的ping检查与复杂的告警系统集成
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pytbox.alert.trigger.ping import ping_with_system, ping_with_victoriametrics, ping_with_callback
from pytbox.alert.lib.insert_alert import insert_alert
from pytbox.alert.lib.load_config import load_config


def create_alert_callback(config: dict):
    """
    创建告警回调函数的工厂函数
    
    Args:
        config (dict): 告警配置
        
    Returns:
        Callable: 告警回调函数
    """
    def alert_callback(target: str):
        """执行完整的告警流程"""
        try:
            insert_alert(
                event_name=config['alert']['ping']['event_name'],
                event_content=f"{target} {config['alert']['ping']['event_name']}",
                entity_name=target,
                priority=config['alert']['ping']['priority'],
                resolved_query={
                    "target": target
                }
            )
            print(f"✅ 成功为目标 {target} 创建告警")
        except Exception as e:
            print(f"❌ 为目标 {target} 创建告警失败: {str(e)}")
    
    return alert_callback


def simple_monitoring_example():
    """简单监控示例：只使用系统ping，不依赖复杂配置"""
    targets = ["8.8.8.8", "1.1.1.1", "192.168.1.1"]
    
    print("=== 简单ping监控示例 ===")
    for target in targets:
        result = ping_with_system(target)
        status_emoji = "✅" if result.data == "通" else "❌"
        print(f"{status_emoji} {target}: {result.data}")


def victoriametrics_monitoring_example():
    """VictoriaMetrics监控示例：需要VM配置"""
    vm_url = "http://your-victoriametrics-url"  # 替换为实际URL
    targets = ["10.30.35.38", "10.30.35.39"]
    
    print("\n=== VictoriaMetrics ping监控示例 ===")
    for target in targets:
        result = ping_with_victoriametrics(
            victoriametrics_url=vm_url,
            target=target,
            last_minutes=5
        )
        status_emoji = "✅" if result.data == "通" else "❌"
        print(f"{status_emoji} {target}: {result.data} ({result.msg})")


def full_alert_integration_example():
    """完整告警集成示例：使用配置文件和告警系统"""
    try:
        # 加载配置（这需要配置文件存在）
        config = load_config()
        
        # 创建告警回调
        alert_callback = create_alert_callback(config)
        
        # 要监控的目标
        targets = ["10.30.35.38", "critical-server.example.com"]
        
        print("\n=== 完整告警集成示例 ===")
        for target in targets:
            result = ping_with_callback(
                target=target,
                checker_func=ping_with_system,
                on_failure=alert_callback
            )
            status_emoji = "✅" if result.data == "通" else "❌"
            print(f"{status_emoji} {target}: {result.data}")
            
    except Exception as e:
        print(f"❌ 完整告警集成失败: {str(e)}")
        print("提示：请确保配置文件存在且告警系统已正确配置")


def custom_alert_handler_example():
    """自定义告警处理示例"""
    
    def custom_alert_handler(target: str):
        """自定义告警处理函数"""
        print(f"🚨 自定义告警：{target} 连接失败！")
        
        # 这里可以添加你自己的告警逻辑，比如：
        # - 发送邮件
        # - 调用webhook
        # - 写入日志文件
        # - 发送短信
        
        # 示例：写入日志文件
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("/tmp/ping_alerts.log", "a") as f:
            f.write(f"[{timestamp}] PING_FAILURE: {target}\n")
    
    print("\n=== 自定义告警处理示例 ===")
    
    # 测试一个不存在的目标
    result = ping_with_callback(
        target="192.168.999.999",  # 故意使用不存在的IP
        checker_func=ping_with_system,
        on_failure=custom_alert_handler
    )
    
    print(f"结果: {result.data} - {result.msg}")


if __name__ == "__main__":
    # 运行各种示例
    simple_monitoring_example()
    
    # 取消注释以下行来测试其他示例
    # victoriametrics_monitoring_example()  # 需要VM配置
    # full_alert_integration_example()      # 需要完整配置
    custom_alert_handler_example()
    
    print("\n=== 示例总结 ===")
    print("1. simple_monitoring_example: 最简单的使用方式，无需任何配置")
    print("2. victoriametrics_monitoring_example: 使用VictoriaMetrics数据源")
    print("3. full_alert_integration_example: 与现有告警系统完整集成")
    print("4. custom_alert_handler_example: 自定义告警处理逻辑")
