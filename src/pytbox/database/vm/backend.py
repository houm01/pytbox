"""
VictoriaMetrics 后端与 fixture 工作流。

后端只需实现一个最小接口：
    - instant_query(promql) -> Dict[str, Any]

内置实现：
    - HTTPBackend: 访问真实 VM HTTP 接口。
    - FileReplayBackend: 从磁盘回放已保存的 JSON fixture。
    - RecordingBackend: 包装 HTTPBackend 并写入 fixture。
    - PromQLCollectorBackend: 仅收集 PromQL 的 dry-run 后端。
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Any, Dict, Optional, List
import requests


class VMBackend:
    """
    VictoriaMetrics 查询后端抽象类。

    子类必须实现：
        instant_query(promql) -> Dict[str, Any]
    """
    def instant_query(self, promql: str) -> Dict[str, Any]:
        """
        执行 instant query 相关逻辑。

        Args:
            promql: promql 参数。

        Returns:
            Any: 返回值。
        """
        raise NotImplementedError


class HTTPBackend(VMBackend):
    """
    真实 HTTP 后端（访问 VM）。

    参数：
        base_url: VM 基础地址，如 "http://vm:8428"。
        timeout: HTTP 超时（秒）。

    说明：
        使用 GET /prometheus/api/v1/query，query 参数为 PromQL。
    """
    def __init__(self, base_url: str, timeout: int = 10):
        """
        初始化对象。

        Args:
            base_url: base_url 参数。
            timeout: timeout 参数。
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def instant_query(self, promql: str) -> Dict[str, Any]:
        """
        执行 PromQL 即时查询（VM HTTP API）。
        """
        url = f"{self.base_url}/prometheus/api/v1/query"
        r = requests.get(url, timeout=self.timeout, params={"query": promql})
        r.raise_for_status()
        return r.json()


class FileReplayBackend(VMBackend):
    """
    回放后端：promql -> fixture JSON。

    每个 promql 映射为 SHA-256 文件名，存放在 fixture_dir 下。
    index.json 用于保存元信息，便于检查。
    """
    def __init__(self, fixture_dir: str):
        """
        初始化对象。

        Args:
            fixture_dir: fixture_dir 参数。
        """
        self.dir = Path(fixture_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _key(promql: str) -> str:
        """
        执行 key 相关逻辑。

        Args:
            promql: promql 参数。

        Returns:
            Any: 返回值。
        """
        return hashlib.sha256(promql.encode("utf-8")).hexdigest()[:16]

    def _index_path(self) -> Path:
        """
        执行 index path 相关逻辑。

        Returns:
            Any: 返回值。
        """
        return self.dir / "index.json"

    def _load_index(self) -> Dict[str, Any]:
        """
        执行 load index 相关逻辑。

        Returns:
            Any: 返回值。
        """
        p = self._index_path()
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            # index 损坏时不要让主流程挂掉：重建一个空的
            return {}

    def _write_index_atomic(self, index: Dict[str, Any]) -> None:
        """
        执行 write index atomic 相关逻辑。

        Args:
            index: index 参数。

        Returns:
            Any: 返回值。
        """
        p = self._index_path()
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(p)  # 原子替换（同文件系统内）



    def path_for(self, promql: str) -> Path:
        """
        执行 path for 相关逻辑。

        Args:
            promql: promql 参数。

        Returns:
            Any: 返回值。
        """
        return self.dir / f"{self._key(promql)}.json"

    def instant_query(self, promql: str) -> Dict[str, Any]:
        """
        读取指定 promql 的 fixture JSON。
        若不存在则抛出 FileNotFoundError。
        """
        p = self.path_for(promql)
        if not p.exists():
            raise FileNotFoundError(
                f"fixture 不存在: {p}\n"
                f"promql: {promql}\n"
                f"提示：请在可访问 VM 的环境运行录制（RecordingBackend）生成该 fixture，再复制到开发环境"
            )
        return json.loads(p.read_text(encoding="utf-8"))

    def save_fixture(
        self,
        promql: str,
        raw_json: Dict[str, Any],
        *,
        meta: Optional[Dict[str, Any]] = None,
        overwrite: bool = True,
    ) -> Path:
        """
        保存 fixture，并写入元信息，同时维护 index.json（方案二）

        meta 建议包含：
        - op: "ping_health"
        - params: {...}
        """
        fixture_path = self.path_for(promql)  # hash 文件名
        filename = fixture_path.name
        now = int(time.time())

        # 1) 如果不覆盖且文件已存在：仍然要确保 index 有记录
        if fixture_path.exists() and not overwrite:
            index = self._load_index()
            # 如果 index 没有该条目，就补上（从 meta/payload 生成最小信息）
            if filename not in index:
                entry = {
                    "promql": promql,
                    "recorded_at": now,
                }
                if meta:
                    # 只保留你关心的字段（也可以直接 entry.update(meta)）
                    if "op" in meta:
                        entry["op"] = meta["op"]
                    if "params" in meta:
                        entry["params"] = meta["params"]
                index[filename] = entry
                self._write_index_atomic(index)
            return fixture_path

        # 2) 组装 payload（写入 fixture 文件本体）
        payload = dict(raw_json)
        payload["_fixture"] = {
            "promql": promql,
            "recorded_at": now,
        }
        if meta:
            payload["_fixture"].update(meta)

        fixture_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 3) 更新 index.json（权威映射）
        index = self._load_index()
        entry = {
            "promql": promql,
            "recorded_at": now,
        }
        if meta:
            if "op" in meta:
                entry["op"] = meta["op"]
            if "params" in meta:
                entry["params"] = meta["params"]

        index[filename] = entry
        self._write_index_atomic(index)

        return fixture_path

class RecordingBackend(VMBackend):
    """
    录制后端：把真实 HTTP 查询的返回保存为 fixture
    并可写入 op/params 等元信息，避免“手写 promql 和代码不一致”

    典型用法：
        http = HTTPBackend("http://vm:8428")
        replay = FileReplayBackend("./tests/fixtures/vm")
        backend = RecordingBackend(
            http, replay, op="ping_health", params={"target": "1.1.1.1"}
        )
    """
    def __init__(
        self,
        http_backend: VMBackend,
        replay_backend: FileReplayBackend,
        *,
        op: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        overwrite: bool = True,
    ):
        """
        初始化对象。

        Args:
            http_backend: http_backend 参数。
            replay_backend: replay_backend 参数。
            op: op 参数。
            params: params 参数。
            overwrite: overwrite 参数。
        """
        self.http = http_backend
        self.replay = replay_backend
        self.op = op
        self.params = params
        self.overwrite = overwrite

    def instant_query(self, promql: str) -> Dict[str, Any]:
        """
        通过 http 后端查询并写入 fixture。
        """
        raw = self.http.instant_query(promql)

        meta: Dict[str, Any] = {}
        if self.op:
            meta["op"] = self.op
        if self.params:
            meta["params"] = self.params

        self.replay.save_fixture(
            promql,
            raw,
            meta=meta or None,
            overwrite=self.overwrite,
        )
        return raw

from typing import Any, Dict, List


class PromQLCollectorBackend:
    """
    Dry-run backend：
    - 不访问 VictoriaMetrics
    - 只收集业务函数内部实际使用到的 PromQL

    测试场景可用于断言生成的 PromQL，无需真实 VM 或 fixture。
    """
    def __init__(self):
        """
        初始化对象。
        """
        self.promqls: List[str] = []

    def instant_query(self, promql: str) -> Dict[str, Any]:
        """
        记录 promql 并返回最小成功结构。
        """
        # 记录 promql
        self.promqls.append(promql)

        # 返回一个“最小可用”的 VM 响应结构
        # 保证 query_instant 不会炸
        return {
            "status": "success",
            "data": {
                "result": []
            }
        }
