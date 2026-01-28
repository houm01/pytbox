import json
import hashlib
import time
from pathlib import Path
from typing import Any, Dict, Optional, List
import requests


class VMBackend:
    def instant_query(self, promql: str) -> Dict[str, Any]:
        raise NotImplementedError


class HTTPBackend(VMBackend):
    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def instant_query(self, promql: str) -> Dict[str, Any]:
        url = f"{self.base_url}/prometheus/api/v1/query"
        r = requests.get(url, timeout=self.timeout, params={"query": promql})
        r.raise_for_status()
        return r.json()


class FileReplayBackend(VMBackend):
    """
    promql -> fixture json 回放
    """
    def __init__(self, fixture_dir: str):
        self.dir = Path(fixture_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _key(promql: str) -> str:
        return hashlib.sha256(promql.encode("utf-8")).hexdigest()[:16]

    def _index_path(self) -> Path:
        return self.dir / "index.json"

    def _load_index(self) -> Dict[str, Any]:
        p = self._index_path()
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            # index 损坏时不要让主流程挂掉：重建一个空的
            return {}

    def _write_index_atomic(self, index: Dict[str, Any]) -> None:
        p = self._index_path()
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(p)  # 原子替换（同文件系统内）



    def path_for(self, promql: str) -> Path:
        return self.dir / f"{self._key(promql)}.json"

    def instant_query(self, promql: str) -> Dict[str, Any]:
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
        self.http = http_backend
        self.replay = replay_backend
        self.op = op
        self.params = params
        self.overwrite = overwrite

    def instant_query(self, promql: str) -> Dict[str, Any]:
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
    """
    def __init__(self):
        self.promqls: List[str] = []

    def instant_query(self, promql: str) -> Dict[str, Any]:
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
