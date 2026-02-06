
"""
VictoriaMetrics 客户端封装（面向业务调用）。

该模块在 VM 后端之上提供：
- 即时查询：返回类型化的 VMInstantSeries 列表
- 批量写入：通过 /api/v1/import (ndjson) 写入样本
- 业务便捷：ping 连续异常检测

与旧版 VictoriaMetrics（src/pytbox/database/victoriametrics.py）不同：
- 这里基于 VMBackend 抽象，可切换 HTTP/回放/录制/采集后端
- 返回统一的 ReturnResponse / VMInstantQueryResponse
- 写入接口支持批量与自动补齐时间戳

典型用法（即时查询）：
    backend = HTTPBackend(base_url="http://vm:8428")
    vm = VictoriaMetricsClient(backend)
    r = vm.query_instant('up{job="node"}')
    if r.code == int(RespCode.OK):
        for s in r.data:
            print(s.labels, s.v)

写入示例（单条）：
    vm.insert(
        "demo_metric",
        labels={"env": "dev", "host": "h1"},
        value=1,
        timestamp_ms=1710000000000,
    )

写入示例（批量）：
    vm.insert_many(
        "demo_metric",
        items=[
            {"labels": {"env": "dev"}, "value": 1},
            {"labels": {"env": "prod"}, "value": 2, "timestamp": 1710000001000},
        ],
        batch_size=500,
    )
"""

import json
import time
import re
from typing import Optional, Literal, Union, Dict, List, Any
from pydantic import ValidationError

import requests

from ...schemas.codes import RespCode
from ...schemas.response import ReturnResponse
from ...schemas.vm_query import VMInstantQueryResponse, VMInstantSeries
from .backend import VMBackend

try:
    from ...schemas.vm_write import VMWriteItem
except Exception:
    VMWriteItem = None  # 允许你先不加模型文件


Number = Union[int, float]

class VictoriaMetricsClient:
    """
    带类型化返回和业务便捷方法的 VM 客户端。

    适用场景：
        - 需要对 VM 即时查询结果进行结构化校验与统一返回
        - 需要批量写入样本到 /api/v1/import
        - 希望使用 fixture/回放的方式做本地开发或测试

    参数：
        backend: VMBackend 实现。HTTPBackend 用于真实 VM，
            FileReplayBackend 用于本地 fixture，RecordingBackend 用于录制 fixture。
        timeout: 写入相关 HTTP 超时（秒）。
        session: 可选 requests.Session，用于连接复用。

    说明：
        - query_instant 会校验 payload 并转换为 VMInstantSeries。
        - insert/insert_many 依赖 backend 提供 base_url（即 HTTPBackend）。
        - 所有方法返回 ReturnResponse（或其子类），包含 code/msg/data。
    """
    def __init__(self, backend: VMBackend, timeout: int = 10, session: Optional[requests.Session] = None, env: str = "prod"):
        """
        初始化对象。

        Args:
            backend: VM 后端实例（HTTP/回放/录制/采集）。
            timeout: 写入接口超时（秒）。
            session: 可选 requests.Session，用于连接复用。
            env: 环境标识（如 dev/prod），用于写入标签或业务判断。
        """
        self.backend = backend
        self.timeout = timeout
        self.session = session or requests.Session()
        self.env = env
        
    def query_instant(
        self,
        query: str,
    ) -> ReturnResponse:
        """
        执行 PromQL 即时查询，并返回类型化序列数据。

        参数:
            query: PromQL 字符串。

        返回:
            ReturnResponse：
                - code == OK：data 为 List[VMInstantSeries]
                - code == NO_DATA：data 为空列表
                - 其他：失败信息在 msg/data 中

        说明:
            - 使用 backend.instant_query 进行实际查询
            - 会对 VM 返回结构进行校验，结构异常时返回 VM_BAD_PAYLOAD
        """
        if not query:
            return ReturnResponse.fail(RespCode.INVALID_PARAMS, "query 不能为空")

        try:
            res_json = self.backend.instant_query(query)
        except Exception as e:
            resp = ReturnResponse.fail(
                RespCode.VM_REQUEST_FAILED,
                f"[{query}] 获取数据失败: {e}",
            )
            return resp

        if res_json.get("status") != "success":
            resp = ReturnResponse.fail(
                RespCode.VM_QUERY_FAILED,
                msg=f"[{query}] 查询失败: {res_json.get('error')}",
                data=res_json,
            )
            return resp

        raw_result = res_json.get("data", {}).get("result", [])
        if not raw_result:
            resp = ReturnResponse.no_data(
                msg=f"[{query}] 没有查询到结果",
                data=[],
            )
            return resp

        try:
            series_list = [VMInstantSeries(**item) for item in raw_result]
        except ValidationError as e:
            resp = ReturnResponse.fail(
                RespCode.VM_BAD_PAYLOAD,
                f"[{query}] 返回结构不符合预期",
                data=str(e),
            )
            return resp

        resp_typed = VMInstantQueryResponse(
            code=int(RespCode.OK),
            msg=f"[{query}] 查询成功!",
            data=series_list,
        )
        return resp_typed

    def _instant_query_raw(self, query: str) -> ReturnResponse:
        """
        执行 PromQL 即时查询并返回原始 result 列表（不做结构校验）。

        Args:
            query: PromQL 字符串。

        Returns:
            ReturnResponse:
                - OK: data 为原始 result 列表
                - NO_DATA: data 为空列表
                - 失败: msg/data 包含错误信息
        """
        if not query:
            return ReturnResponse.fail(RespCode.INVALID_PARAMS, "query 不能为空")

        try:
            res_json = self.backend.instant_query(query)
        except Exception as e:
            return ReturnResponse.fail(
                RespCode.VM_REQUEST_FAILED,
                f"[{query}] 获取数据失败: {e}",
            )

        if res_json.get("status") != "success":
            return ReturnResponse.fail(
                RespCode.VM_QUERY_FAILED,
                msg=f"[{query}] 查询失败: {res_json.get('error')}",
                data=res_json,
            )

        raw_result = res_json.get("data", {}).get("result", [])
        if not raw_result:
            return ReturnResponse.no_data(
                msg=f"[{query}] 没有查询到结果",
                data=[],
            )

        return ReturnResponse.ok(
            msg=f"[{query}] 查询成功!",
            data=raw_result,
        )

    def _query_raw(self, query: str, dev_file: Optional[str] = None) -> ReturnResponse:
        """
        即时查询原始 result，支持 dev_file 覆盖。

        Args:
            query: PromQL 字符串。
            dev_file: 可选开发数据文件路径（用于本地回放）。

        Returns:
            ReturnResponse: 统一响应，data 为原始 result 列表或 dev 文件内容。
        """
        if dev_file:
            try:
                from ...utils.load_vm_devfile import load_dev_file
            except Exception as e:
                return ReturnResponse.fail(
                    RespCode.INTERNAL_ERROR,
                    f"加载 dev_file 失败: {e}",
                )

            r = load_dev_file(dev_file)
            # 兼容开发文件格式
            data = getattr(r, "data", None)
            if isinstance(data, dict):
                result = data.get("data", {}).get("result")
                if result is not None:
                    return ReturnResponse.ok(msg=r.msg, data=result)
            return ReturnResponse.ok(msg=r.msg, data=data)

        return self._instant_query_raw(query)

    def _get_base_url(self) -> str:
        """
        获取 HTTP API 的 base_url。

        Returns:
            str: 规范化后的 base_url（去除尾部斜杠）。

        Raises:
            RuntimeError: backend 未提供 base_url 时抛出。
        """
        base_url = getattr(self.backend, "base_url", None)
        if not base_url:
            raise RuntimeError(f"{self.backend.__class__.__name__} 不支持 HTTP 接口（缺少 base_url）")
        return str(base_url).rstrip("/")

    def _get_write_base_url(self) -> str:
        """
        获取写入 API 的 base_url。

        Returns:
            str: 规范化后的 base_url（去除尾部斜杠）。

        Raises:
            RuntimeError: backend 未提供 base_url 时抛出。
        """
        return self._get_base_url()

    def _normalize_labels(self, raw: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """
        规范化 labels，将所有值转为字符串。

        Args:
            raw: 原始标签字典。

        Returns:
            Dict[str, str]: 规范化后的标签字典。
        """
        if not raw:
            return {}
        return {k: "None" if v is None else str(v) for k, v in raw.items()}

    def _post_ndjson(self, lines: List[Dict[str, Any]]) -> None:
        """
        发送 NDJSON 写入请求到 /api/v1/import。

        Args:
            lines: 已组装好的 payload 列表。

        Raises:
            RuntimeError: HTTP 状态码 >= 300 时抛出。
        """
        base_url = self._get_write_base_url()
        url = f"{base_url}/api/v1/import"
        body = ("\n".join(json.dumps(x, ensure_ascii=False) for x in lines) + "\n").encode("utf-8")
        headers = {"Content-Type": "application/x-ndjson"}
        resp = self.session.post(url, data=body, headers=headers, timeout=self.timeout)
        if resp.status_code >= 300:
            raise RuntimeError(f"http={resp.status_code} body={resp.text}")

    def query(self, query: Optional[str] = None, output_format: Optional[Literal["json"]] = None) -> Union[ReturnResponse, str]:
        """
        即时查询（原始 result 结构）。

        Args:
            query: PromQL 字符串。
            output_format: 设为 "json" 时返回 JSON 字符串。

        Returns:
            ReturnResponse 或 JSON 字符串。
        """
        resp = self._instant_query_raw(query or "")
        if output_format == "json":
            try:
                return json.dumps(resp.model_dump(), ensure_ascii=False)
            except Exception:
                return json.dumps(resp.dict(), ensure_ascii=False)  # 兼容旧版本 pydantic
        return resp

    def query_range(self, query: str, start: str = "-1d", step: str = "1h", end: Optional[str] = None) -> ReturnResponse:
        """
        查询时间范围内的序列（query_range）。

        Args:
            query: PromQL 字符串。
            start: 起始时间（VM 支持相对时间，如 -1d）。
            step: 采样步长（如 1m、5m、1h）。
            end: 结束时间（可选，不传则由 VM 处理）。

        Returns:
            ReturnResponse: data 为 VM 返回 JSON。
        """
        try:
            base_url = self._get_base_url()
        except Exception as e:
            return ReturnResponse.fail(RespCode.VM_REQUEST_FAILED, str(e))

        url = f"{base_url}/prometheus/api/v1/query_range"
        params: Dict[str, Any] = {"query": query, "start": start, "step": step}
        if end is not None:
            params["end"] = end

        try:
            r = self.session.get(url, timeout=self.timeout, params=params)
            r.raise_for_status()
            res_json = r.json()
        except Exception as e:
            return ReturnResponse.fail(RespCode.VM_REQUEST_FAILED, f"[{query}] 查询失败: {e}")

        return ReturnResponse.ok(msg=f"[{query}] 查询成功!", data=res_json)

    def get_labels(self, metric_name: str) -> ReturnResponse:
        """
        获取指定指标的 labels 列表。

        Args:
            metric_name: 指标名或匹配表达式。

        Returns:
            ReturnResponse: data 为 labels 列表。
        """
        try:
            base_url = self._get_base_url()
        except Exception as e:
            return ReturnResponse.fail(RespCode.VM_REQUEST_FAILED, str(e))

        url = f"{base_url}/api/v1/series"
        try:
            response = self.session.get(url, timeout=self.timeout, params={"match[]": metric_name})
            response.raise_for_status()
            results = response.json()
        except Exception as e:
            return ReturnResponse.fail(RespCode.VM_REQUEST_FAILED, f"获取 labels 失败: {e}")

        if results.get("status") == "success":
            data = results.get("data", [])
            return ReturnResponse.ok(
                msg=f"metric name: {metric_name} 获取到 {len(data)} 条数据",
                data=data,
            )

        return ReturnResponse.fail(
            RespCode.VM_QUERY_FAILED,
            msg=f"metric name: {metric_name} 查询失败",
            data=results,
        )
    
    def insert(
        self,
        metric_name: str,
        labels: Optional[Dict[str, Any]] = None,
        value: Optional[Number] = None,
        timestamp_ms: Optional[int] = None,
    ) -> ReturnResponse:
        """
        写入单条样本。

        参数:
            metric_name: 指标名（写入时会作为 __name__）。
            labels: 标签字典（值会转成字符串）。
            value: 样本值（None 默认写 1）。
            timestamp_ms: 毫秒时间戳（None 自动生成）。

        返回:
            ReturnResponse，data 中包含 {"inserted": 1}。

        说明:
            - 实际调用 insert_many，batch_size=1
        """
        return self.insert_many(metric_name, [{"labels": labels, "value": value, "timestamp": timestamp_ms}], batch_size=1)

    def insert_many(
        self,
        metric_name: str,
        items: List[Dict[str, Any]],
        batch_size: int = 500,
    ) -> ReturnResponse:
        """
        批量写入样本（/api/v1/import，ndjson）。

        items 内每个元素支持:
            - labels: Dict[str, Any]
            - value: Number（None => 1）
            - timestamp: 毫秒时间戳（None => 自动生成）

        参数:
            metric_name: 指标名。
            items: 待写入条目列表。
            batch_size: 每次请求最大条数。

        返回:
            ReturnResponse，data 中包含 {"inserted": N}。

        说明:
            - 为缺失 timestamp 的条目自动补齐时间戳（保持唯一）
            - 写入失败时返回已写入数量，便于重试或告警
        """
        if not metric_name:
            return ReturnResponse.fail(RespCode.INVALID_PARAMS, "metric_name 不能为空")

        if not items:
            return ReturnResponse.ok(msg="[vm][insert_many] empty items, skip", data={"inserted": 0})

        base_ts = int(time.time() * 1000)
        inserted = 0
        bs = max(1, batch_size)

        try:
            for start in range(0, len(items), bs):
                chunk = items[start:start + bs]
                lines: List[Dict[str, Any]] = []

                for i, item in enumerate(chunk):
                    labels = self._normalize_labels(item.get("labels") or {})
                    v = 1 if item.get("value") is None else item.get("value")
                    ts = item.get("timestamp")
                    if ts is None:
                        ts = base_ts + inserted + i

                    lines.append({
                        "metric": {"__name__": metric_name, **labels},
                        "values": [v],
                        "timestamps": [int(ts)],
                    })

                self._post_ndjson(lines)
                inserted += len(chunk)

            return ReturnResponse.ok(
                msg=f"[vm][insert_many][ok] metric={metric_name} inserted={inserted}",
                data={"inserted": inserted},
            )

        except Exception as e:
            return ReturnResponse.fail(
                RespCode.VM_REQUEST_FAILED,
                msg=f"[vm][insert_many][fail] metric={metric_name} error={e}",
                data={"inserted": inserted},
            )

    def ping_health(
        self,
        target: Optional[str] = None,
        last_minutes: int = 10,
    ) -> ReturnResponse:
        """
        查询最近 N 分钟内“持续异常”的 ping 目标（抗抖动）

        PromQL 规则：
        - min_over_time(ping_result_code[Nm]) > 0
        - 只返回持续异常的 series

        参数:
            target: 可选 target 标签过滤。
            last_minutes: 回溯分钟数（必须为正）。

        返回:
            ReturnResponse：
                - OK：无持续异常（data == []）
                - PING_UNHEALTHY：存在持续异常（data 含 target 列表）
                - 其他：后端/校验错误

        说明:
            - 语义上“无返回结果”代表最近 N 分钟没有持续异常
            - data 中包含 target、value、labels，便于直接展示或告警
        """
        if last_minutes <= 0:
            return ReturnResponse.fail(
                RespCode.INVALID_PARAMS,
                "last_minutes 必须为正整数",
            )

        if target:
            promql = (
                f'min_over_time('
                f'ping_result_code{{target="{target}"}}'
                f'[{last_minutes}m]) > 0'
            )
        else:
            promql = (
                f'min_over_time('
                f'ping_result_code'
                f'[{last_minutes}m]) > 0'
            )

        r = self.query_instant(promql)

        if isinstance(r, str):
            return ReturnResponse.fail(
                RespCode.INTERNAL_ERROR,
                "内部错误：query_instant 返回了 json 字符串",
            )

        # 查询失败，直接返回
        if r.code != int(RespCode.OK) and r.code != int(RespCode.NO_DATA):
            return r

        # ⭐ 关键语义：没有返回任何 series = 没有持续异常
        if not r.data:
            return ReturnResponse.ok(
                msg=(
                    f"最近 {last_minutes} 分钟无持续 ping 异常"
                    + (f"（target={target}）" if target else "")
                ),
                data=[],
            )

        # 有结果：全部都是“持续异常”的 target
        return ReturnResponse(
            code=int(RespCode.PING_UNHEALTHY),
            msg=(
                f"最近 {last_minutes} 分钟存在持续 ping 异常"
                + (f"（target={target}）" if target else "")
            ),
            data=[
                {
                    "target": s.label("target"),
                    "value": s.v,
                    "labels": s.labels,
                }
                for s in r.data
            ],
        )

    def check_ping_result(
        self,
        target: str,
        last_minute: int = 10,
        env: str = "prod",
        dev_file: str = "",
    ) -> ReturnResponse:
        """
        检查 ping 结果（单目标）。

        Args:
            target: 目标地址或 target 标签值。
            last_minute: 最近多少分钟。
            env: 环境标识（兼容旧接口，不影响逻辑）。
            dev_file: 可选开发数据文件路径。

        Returns:
            ReturnResponse:
                - OK: 正常
                - PING_UNHEALTHY: 异常
                - NO_DATA: 无数据
        """
        _ = env
        query = f'min_over_time(ping_result_code{{target="{target}"}}[{last_minute}m])'
        r = self._query_raw(query, dev_file=dev_file or None)

        if r.code == int(RespCode.NO_DATA):
            return ReturnResponse.no_data(
                msg=f"未查询到 {target} 最近 {last_minute} 分钟数据",
                data=[],
            )

        if r.code != int(RespCode.OK):
            return r

        try:
            value = r.data[0].get("values", r.data[0].get("value"))[1]
        except Exception:
            return ReturnResponse.fail(
                RespCode.VM_BAD_PAYLOAD,
                msg=f"{target} 返回结构不符合预期",
                data=r.data,
            )

        if str(value) == "0" or float(value) == 0:
            return ReturnResponse.ok(
                msg=f"已检查 {target} 最近 {last_minute} 分钟是正常的!",
                data=r.data,
            )

        return ReturnResponse(
            code=int(RespCode.PING_UNHEALTHY),
            msg=f"已检查 {target} 最近 {last_minute} 分钟是异常的!",
            data=r.data,
        )

    def check_unreachable_ping_result(self, dev_file: str = "") -> ReturnResponse:
        """
        检查不可达的 ping 结果（全量）。

        Args:
            dev_file: 可选开发数据文件路径。

        Returns:
            ReturnResponse: 查询结果（raw result 列表）。
        """
        query = "ping_result_code == 1"
        return self._query_raw(query, dev_file=dev_file or None)

    def check_interface_rate(
        self,
        direction: Literal["in", "out"],
        sysname: str,
        ifname: str,
        last_n_minutes: Optional[int] = None,
        dev_file: str = None,
    ) -> ReturnResponse:
        """
        查询指定设备接口最近 N 分钟速率（Mbit/s）。

        Args:
            direction: in/out。
            sysname: 设备 sysName。
            ifname: 接口 ifName。
            last_n_minutes: 时间窗口（分钟）。
            dev_file: 可选开发数据文件路径。

        Returns:
            ReturnResponse: data 中包含 query 与数值。
        """
        if not last_n_minutes or last_n_minutes <= 0:
            return ReturnResponse.fail(RespCode.INVALID_PARAMS, "last_n_minutes 必须为正整数")

        if direction == "in":
            query = (
                f'(rate(snmp_interface_ifHCInOctets{{sysName="{sysname}", ifName="{ifname}"}}'
                f'[{last_n_minutes}m])) * 8 / 1000000'
            )
        else:
            query = (
                f'(rate(snmp_interface_ifHCOutOctets{{sysName="{sysname}", ifName="{ifname}"}}'
                f'[{last_n_minutes}m])) * 8 / 1000000'
            )

        r = self._query_raw(query, dev_file=dev_file)
        if r.code != int(RespCode.OK):
            return ReturnResponse.fail(
                RespCode.VM_QUERY_FAILED,
                msg=f"查询 {sysname} {ifname} 失败: {r.msg}",
                data={"query": query, "data": None},
            )

        try:
            value = float(r.data[0]["value"][1])
        except Exception:
            return ReturnResponse.fail(
                RespCode.VM_BAD_PAYLOAD,
                msg="返回结构不符合预期",
                data=r.data,
            )

        return ReturnResponse.ok(
            msg=f"{sysname} {ifname} 最近 {last_n_minutes} 分钟 {direction} 方向流量速率为 {int(value)} Mbit/s",
            data={"query": query, "data": int(value)},
        )

    def check_interface_avg_rate(
        self,
        direction: Literal["in", "out"],
        sysname: str,
        ifname: str,
        last_hours: Optional[int] = 24,
        last_minutes: Optional[int] = 5,
    ) -> ReturnResponse:
        """
        查询指定接口最近 N 小时的平均速率（Mbit/s）。
        """
        if direction == "in":
            query = (
                f'avg_over_time((rate(snmp_interface_ifHCInOctets{{sysName="{sysname}", ifName="{ifname}"}}'
                f'[{last_minutes}m]) * 8) [{last_hours}h:]) / 1e6'
            )
        else:
            query = (
                f'avg_over_time((rate(snmp_interface_ifHCOutOctets{{sysName="{sysname}", ifName="{ifname}"}}'
                f'[{last_minutes}m]) * 8) [{last_hours}h:]) / 1e6'
            )

        r = self._query_raw(query)
        if r.code != int(RespCode.OK):
            return ReturnResponse.fail(
                RespCode.VM_QUERY_FAILED,
                msg=f"查询 {sysname} {ifname} 最近 {last_hours} 小时平均速率失败: {r.msg}",
            )

        try:
            rate = float(r.data[0]["value"][1])
        except Exception:
            return ReturnResponse.fail(
                RespCode.VM_BAD_PAYLOAD,
                msg=f"查询 {sysname} {ifname} 最近 {last_hours} 小时平均速率为 0 Mbit/s",
            )

        return ReturnResponse.ok(
            msg=f"查询 {sysname} {ifname} 最近 {last_hours} 小时平均速率为 {round(rate, 2)} Mbit/s",
            data=round(rate, 2),
        )

    def check_interface_max_rate(
        self,
        direction: Literal["in", "out"],
        sysname: str,
        ifname: str,
        last_hours: Optional[int] = 24,
        last_minutes: Optional[int] = 5,
    ) -> ReturnResponse:
        """
        查询指定接口最近 N 小时的最大速率（Mbit/s）。
        """
        if direction == "in":
            query = (
                f'max_over_time((rate(snmp_interface_ifHCInOctets{{sysName="{sysname}", ifName="{ifname}"}}'
                f'[{last_minutes}m]) * 8) [{last_hours}h:]) / 1e6'
            )
        else:
            query = (
                f'max_over_time((rate(snmp_interface_ifHCOutOctets{{sysName="{sysname}", ifName="{ifname}"}}'
                f'[{last_minutes}m]) * 8) [{last_hours}h:]) / 1e6'
            )

        r = self._query_raw(query)
        if r.code != int(RespCode.OK):
            return ReturnResponse.fail(
                RespCode.VM_QUERY_FAILED,
                msg=f"查询 {sysname} {ifname} 最近 {last_hours} 小时最大速率失败: {r.msg}",
            )

        try:
            rate = float(r.data[0]["value"][1])
        except Exception:
            return ReturnResponse.fail(
                RespCode.VM_BAD_PAYLOAD,
                msg=f"查询 {sysname} {ifname} 最近 {last_hours} 小时最大速率为 0 Mbit/s",
            )

        return ReturnResponse.ok(
            msg=f"查询 {sysname} {ifname} 最近 {last_hours} 小时最大速率为 {round(rate, 2)} Mbit/s",
            data=round(rate, 2),
        )

    def check_snmp_port_status(
        self,
        sysname: str = None,
        if_name: str = None,
        last_minute: int = 5,
        dev_file: str = None,
    ) -> ReturnResponse:
        """
        查询端口状态（up/down）。
        """
        query = f'avg_over_time(snmp_interface_ifOperStatus{{sysName="{sysname}", ifName="{if_name}"}}[{last_minute}m])'
        r = self._query_raw(query, dev_file=dev_file)
        if r.code != int(RespCode.OK):
            return r

        try:
            status_code = int(float(r.data[0]["value"][1]))
        except Exception:
            return ReturnResponse.fail(RespCode.VM_BAD_PAYLOAD, "返回结构不符合预期", data=r.data)

        status = "up" if status_code == 1 else "down"
        return ReturnResponse.ok(
            msg=f"{sysname} {if_name} 最近 {last_minute} 分钟端口状态为 {status}",
            data=status,
        )

    def insert_cronjob_run_status(
        self,
        app_type: Literal["alert", "meraki", "other"] = "other",
        app: str = "",
        status_code: Literal[0, 1] = 1,
        comment: str = None,
        schedule_interval: str = None,
        schedule_cron: str = None,
    ) -> ReturnResponse:
        """
        写入 cronjob 运行状态指标。
        """
        labels = {"app": app, "env": self.env}
        if app_type:
            labels["app_type"] = app_type
        if comment:
            labels["comment"] = comment

        if schedule_interval:
            labels["schedule_type"] = "interval"
            labels["schedule_interval"] = schedule_interval

        if schedule_cron:
            labels["schedule_type"] = "cron"
            labels["schedule_cron"] = schedule_cron

        return self.insert(metric_name="cronjob_run_status", labels=labels, value=status_code)

    def insert_cronjob_duration_seconds(
        self,
        app_type: Literal["alert", "meraki", "other"] = "other",
        app: str = "",
        duration_seconds: float = None,
        comment: str = None,
        schedule_interval: str = None,
        schedule_cron: str = None,
    ) -> ReturnResponse:
        """
        写入 cronjob 执行耗时指标（秒）。
        """
        labels = {"app": app, "env": self.env}
        if app_type:
            labels["app_type"] = app_type
        if comment:
            labels["comment"] = comment

        if schedule_interval:
            labels["schedule_type"] = "interval"
            labels["schedule_interval"] = schedule_interval

        if schedule_cron:
            labels["schedule_type"] = "cron"
            labels["schedule_cron"] = schedule_cron

        return self.insert(
            metric_name="cronjob_run_duration_seconds",
            labels=labels,
            value=duration_seconds,
        )

    def get_vmware_esxhostnames(self, vcenter: str = None) -> ReturnResponse:
        """
        获取 vCenter 下的 ESXi 主机名列表。
        """
        query = f'vsphere_host_sys_uptime_latest{{vcenter="{vcenter}"}}'
        r = self._query_raw(query)
        if r.code != int(RespCode.OK):
            return r

        esxhostnames = []
        for metric in r.data:
            labels = metric.get("metric") or metric.get("labels") or {}
            esxhostname = labels.get("esxhostname")
            if esxhostname:
                esxhostnames.append(esxhostname)

        return ReturnResponse.ok(
            msg=f"获取到 {len(esxhostnames)} 台 ESXi 主机",
            data=esxhostnames,
        )

    def get_vmware_cpu_usage(self, vcenter: str = None, esxhostname: str = None) -> ReturnResponse:
        """
        获取指定 ESXi 主机 CPU 使用率。
        """
        query = f'vsphere_host_cpu_usage_average{{vcenter="{vcenter}", esxhostname="{esxhostname}"}}'
        r = self._query_raw(query)
        if r.code != int(RespCode.OK):
            return r

        try:
            value = float(r.data[0]["value"][1])
        except Exception:
            return ReturnResponse.fail(RespCode.VM_BAD_PAYLOAD, "返回结构不符合预期", data=r.data)

        return ReturnResponse.ok(msg="查询成功", data=value)

    def get_vmware_memory_usage(self, vcenter: str = None, esxhostname: str = None) -> ReturnResponse:
        """
        获取指定 ESXi 主机内存使用率。
        """
        query = f'vsphere_host_mem_usage_average{{vcenter="{vcenter}", esxhostname="{esxhostname}"}}'
        r = self._query_raw(query)
        if r.code != int(RespCode.OK):
            return r

        try:
            value = float(r.data[0]["value"][1])
        except Exception:
            return ReturnResponse.fail(RespCode.VM_BAD_PAYLOAD, "返回结构不符合预期", data=r.data)

        return ReturnResponse.ok(msg="查询成功", data=value)

    def get_snmp_interfaces(self, sysname: str) -> ReturnResponse:
        """
        获取设备全部接口的 SNMP 状态。
        """
        return self._query_raw(query=f'snmp_interface_ifOperStatus{{sysName="{sysname}"}}')

    def get_snmp_interface_oper_status(
        self,
        sysname: str = None,
        ifname: str = None,
        sysname_repr: str = None,
        ifname_list: Optional[List[str]] = None,
        dev_file: str = None,
    ) -> ReturnResponse:
        """
        获取指定接口的 SNMP oper status。
        """
        if dev_file is not None:
            return self._query_raw(query="", dev_file=dev_file)

        if ifname_list and sysname_repr:
            ifname_pattern = "|".join([re.escape(name) for name in ifname_list])
            query = f'snmp_interface_ifOperStatus{{sysName=~"{sysname_repr}", ifName=~"^({ifname_pattern})$"}}'
        else:
            query = f'snmp_interface_ifOperStatus{{sysName="{sysname}", ifName="{ifname}"}}'

        return self._query_raw(query=query)

    def get_viptela_bfd_sessions_up(
        self,
        sysname: str = None,
        session_up_lt: int = None,
        session_up_gt: int = None,
        last_minute: int = 10,
        dev_file: str = None,
    ) -> ReturnResponse:
        """
        获取 viptela BFD 会话数（支持阈值比较）。
        """
        if dev_file is not None:
            r = self._query_raw(query="", dev_file=dev_file)
        else:
            if sysname is None:
                if session_up_lt is not None:
                    query = f'max_over_time(vedge_snmp_bfdSummaryBfdSessionsUp[{last_minute}m]) < {session_up_lt}'
                elif session_up_gt is not None:
                    query = f'max_over_time(vedge_snmp_bfdSummaryBfdSessionsUp[{last_minute}m]) > {session_up_gt}'
                else:
                    return ReturnResponse.fail(
                        RespCode.INVALID_PARAMS,
                        "sysname 和 session_up_lt 或 session_up_gt 不能同时为空",
                    )
            else:
                if session_up_gt is None:
                    return ReturnResponse.fail(RespCode.INVALID_PARAMS, "session_up_gt 不能为空")
                query = f'max_over_time(vedge_snmp_bfdSummaryBfdSessionsUp{{sysName=\"{sysname}\"}}[{last_minute}m]) > {session_up_gt}'

            r = self._query_raw(query=query)

        if r.code == int(RespCode.NO_DATA):
            return ReturnResponse.no_data(msg="满足条件的有 0 条数据", data=[])

        if r.code != int(RespCode.OK):
            return r

        data = []
        for result in r.data:
            metric = result.get("metric") or result.get("labels") or {}
            data.append(
                {
                    "agent_host": metric.get("agent_host"),
                    "sysname": metric.get("sysName"),
                    "value": int(float(result["value"][1])),
                }
            )

        return ReturnResponse.ok(msg=f"满足条件的有 {len(data)} 条", data=data)

    def get_viptela_bfd_session_list_state(
        self,
        sysname: str = None,
        last_minute: int = 30,
        dev_file: str = None,
    ) -> ReturnResponse:
        """
        获取 viptela BFD 会话列表状态。
        """
        if dev_file is not None:
            query = None
            r = self._query_raw(query="", dev_file=dev_file)
        else:
            query = f"""limitk(12,
                sort_desc(
                    max_over_time(
                        vedge_snmp_bfd_bfdSessionsListState{{sysName="{sysname}"}}[{last_minute}m]
                    )
                )
            )"""
            r = self._query_raw(query=query)

        if r.code != int(RespCode.OK):
            return r

        data = []
        for result in r.data:
            metric = result.get("metric") or result.get("labels") or {}
            data.append(metric | {"value": result["value"][1]})

        return ReturnResponse.ok(
            msg=f"获取到 {len(data)} 条数据",
            data={"query": query, "data": data},
        )

    def get_apc_input_status(
        self,
        sysname: str = None,
        last_minutes: int = 5,
        threshold: int = 3,
        dev_file: str = None,
    ) -> ReturnResponse:
        """
        获取 UPS 输入状态。
        """
        if sysname is None:
            query = (
                "count_over_time((snmp_upsInput_upsAdvInputLineVoltage < 1)"
                f"[{last_minutes}m:1m]) >= {threshold}"
            )
        else:
            query = (
                "count_over_time((snmp_upsInput_upsAdvInputLineVoltage"
                f'{{sysName="{sysname}"}} <= 1)[3m:1m]) == 0'
            )

        r = self._query_raw(query=query, dev_file=dev_file)
        if r.code not in (int(RespCode.OK), int(RespCode.NO_DATA)):
            return ReturnResponse.fail(r.code, r.msg, data={"query": query, "data": None})

        data = r.data or []
        if sysname is None:
            status = "fault" if len(data) > 0 else "normal"
            status_msg = "存在中断设备" if len(data) > 0 else "未发现中断设备"
            mode = "fault_check"
        else:
            status = "normal" if len(data) > 0 else "fault"
            status_msg = "市电已恢复" if len(data) > 0 else "市电仍中断"
            mode = "recovery_check"

        return ReturnResponse.ok(
            msg=status_msg,
            data={
                "query": query,
                "data": data,
                "status": status,
                "status_msg": status_msg,
                "mode": mode,
                "sysname": sysname,
            },
        )

    def get_apc_battery_replace_status(
        self,
        sysname: str = None,
        last_minutes: int = 5,
        threshold: int = 3,
        dev_file: str = None,
    ) -> ReturnResponse:
        """
        获取 UPS 电池更换状态。
        """
        if sysname is None:
            query = (
                "count_over_time((snmp_upsBattery_upsAdvBatteryReplaceIndicator == 2)"
                f"[{last_minutes}m:1m]) >= {threshold}"
            )
        else:
            query = (
                "count_over_time((snmp_upsBattery_upsAdvBatteryReplaceIndicator"
                f'{{sysName="{sysname}"}} == 2)[{threshold}m:1m]) == 0'
            )

        r = self._query_raw(query=query, dev_file=dev_file)
        if r.code not in (int(RespCode.OK), int(RespCode.NO_DATA)):
            return ReturnResponse.fail(r.code, r.msg, data={"query": query, "data": None})

        data = r.data or []
        if sysname is None:
            status = "fault" if len(data) > 0 else "normal"
            status_msg = "存在需要更换电池的设备" if len(data) > 0 else "未发现需要更换电池的设备"
            mode = "fault_check"
        else:
            status = "normal" if len(data) > 0 else "fault"
            status_msg = "电池更换告警已恢复" if len(data) > 0 else "电池更换告警仍存在"
            mode = "recovery_check"

        return ReturnResponse.ok(
            msg=status_msg,
            data={
                "query": query,
                "data": data,
                "status": status,
                "status_msg": status_msg,
                "mode": mode,
                "sysname": sysname,
            },
        )

    def get_system_uptime(
        self,
        sysname: str = None,
        uptime_lt_minute: int = None,
        dev_file: str = None,
    ) -> ReturnResponse:
        """
        获取系统 uptime（分钟）。
        """
        if sysname is None and uptime_lt_minute is not None:
            query = f"snmp_sysUpTime < {uptime_lt_minute * 60}"
        else:
            query = f'snmp_sysUpTime{{sysName="{sysname}"}}'

        r = self._query_raw(query=query, dev_file=dev_file)
        if r.code != int(RespCode.OK):
            return ReturnResponse.fail(r.code, r.msg, data={"query": query, "data": None})

        try:
            uptime_minute = int(float(r.data[0]["value"][1]) / 60)
        except Exception:
            return ReturnResponse.fail(RespCode.VM_BAD_PAYLOAD, "返回结构不符合预期", data=r.data)

        return ReturnResponse.ok(
            msg=f"获取到 {len(r.data)} 条数据",
            data={"query": query, "data": r.data, "uptime_minute": uptime_minute},
        )
