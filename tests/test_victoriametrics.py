#!/usr/bin/env python3

# from pytbox.database.vm.client import VictoriaMetricsClient
# from pytbox.database.vm.backend import FileReplayBackend, PromQLCollectorBackend

from pytbox.base import get_vm_client

client = get_vm_client()




# 打印 promql 命令
# collector_backend = PromQLCollectorBackend()
# promql_client = VictoriaMetricsClient(collector_backend)

# # 你要调试哪个业务函数，就调用哪个
# promql_client.ping_health(last_minutes=10)                 # 全量
# promql_client.ping_health(target="10.20.3.108", last_minutes=10)

# print("\n=== PromQL used ===")
# for q in collector_backend.promqls:
#     print(q)

# 调用方法 / 生产
# from pytbox.database.vm.backend import HTTPBackend
# from pytbox.database.vm.client import VictoriaMetricsClient

# backend = HTTPBackend(base_url="http://vm:8428", timeout=10)
# client = VictoriaMetricsClient(backend)

# # 1) 直接查 PromQL（instant）
# r = client.query_instant('up')
# print(r.code, r.msg)
# # r.data 是 List[VMInstantSeries]

# # 2) 查业务函数（推荐：不用手写 PromQL）
# r = client.ping_health(last_minutes=10)  # 全量检查持续异常
# print(r)

# r = client.ping_health(target="10.20.3.108", last_minutes=10)  # 单 target
# print(r)

# 调用方法 / 测试
# from pytbox.database.vm.backend import FileReplayBackend
# from pytbox.database.vm.client import VictoriaMetricsClient

# backend = FileReplayBackend(fixture_dir="tests/fixtures/vm")
# client = VictoriaMetricsClient(backend)

# # 业务代码照常调用（它会根据 promql 自动找到对应 json）
# r = client.ping_health(last_minutes=10)
# print(r)

# # 或者直接查某条 promql（必须有对应 fixture）
# r = client.query_instant('min_over_time(ping_result_code[10m]) > 0')
# print(r)


# 开发环境测试
# backend = HTTPBackend(base_url="http://vm:8428", timeout=10)
# client = VictoriaMetricsClient(backend)

# r = client.ping_health(last_minutes=10)
# print(r)

# r = client.ping_health(target="10.20.3.108", last_minutes=10)
# print(r)

# r = client.insert(metric_name="test_metric", labels={"key": "value"}, value=1)
# print(r)

import time

base_ts = int(time.time() * 1000)

items = [
    {
        "labels": {
            "target": "10.20.3.108",
            "env": "prod",
            "isp": "ct",
        },
        "value": 0,
        "timestamp": base_ts - 5000,
    },
    {
        "labels": {
            "target": "10.20.3.109",
            "env": "prod",
            "isp": "ct",
        },
        "value": 1,
        # timestamp 缺失 -> 自动补齐
    },
]

resp = client.insert_many(
    metric_name="test_metric",
    items=items,
    batch_size=500,
)

print(resp)
