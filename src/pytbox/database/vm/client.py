
import json
import time
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
    def __init__(self, backend: VMBackend, timeout: int = 10, session: Optional[requests.Session] = None):
        self.backend = backend
        self.timeout = timeout
        self.session = session or requests.Session()
        
    def query_instant(
        self,
        query: str,
    ) -> ReturnResponse:
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

    def _get_write_base_url(self) -> str:
        base_url = getattr(self.backend, "base_url", None)
        if not base_url:
            raise RuntimeError(f"{self.backend.__class__.__name__} 不支持写入（缺少 base_url）")
        return str(base_url).rstrip("/")

    def _normalize_labels(self, raw: Optional[Dict[str, Any]]) -> Dict[str, str]:
        if not raw:
            return {}
        return {k: "None" if v is None else str(v) for k, v in raw.items()}

    def _post_ndjson(self, lines: List[Dict[str, Any]]) -> None:
        base_url = self._get_write_base_url()
        url = f"{base_url}/api/v1/import"
        body = ("\n".join(json.dumps(x, ensure_ascii=False) for x in lines) + "\n").encode("utf-8")
        headers = {"Content-Type": "application/x-ndjson"}
        resp = self.session.post(url, data=body, headers=headers, timeout=self.timeout)
        if resp.status_code >= 300:
            raise RuntimeError(f"http={resp.status_code} body={resp.text}")
    
    def insert(
        self,
        metric_name: str,
        labels: Optional[Dict[str, Any]] = None,
        value: Optional[Number] = None,
        timestamp_ms: Optional[int] = None,
    ) -> ReturnResponse:
        return self.insert_many(metric_name, [{"labels": labels, "value": value, "timestamp": timestamp_ms}], batch_size=1)

    def insert_many(
        self,
        metric_name: str,
        items: List[Dict[str, Any]],
        batch_size: int = 500,
    ) -> ReturnResponse:
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