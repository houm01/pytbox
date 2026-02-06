# Dida365 使用文档

本文档说明 `pytbox` 中 `Dida365` 客户端的初始化、常用调用方式和 live 测试方法。

## 1. 初始化

```python
from pytbox.dida365 import Dida365

dida = Dida365(
    access_token="YOUR_DIDA_ACCESS_TOKEN",
    cookie="YOUR_DIDA_COOKIE",
    timeout=3,                 # 单次请求超时（秒）
    max_retries=3,             # 最大重试次数（内部最多 3）
    retry_backoff_base=0.5,    # 指数退避基数（秒）
    idempotency_ttl_seconds=300,  # 写操作幂等窗口（秒）
)
```

## 2. 返回契约

所有外部 IO 方法统一返回 `src/pytbox/schemas/response.py::ReturnResponse`：

- `code`: `0` 表示成功，非 `0` 表示失败
- `msg`: 状态描述
- `data`: 业务数据

建议统一判断：

```python
resp = dida.get_projects()
if resp.code != 0:
    raise RuntimeError(resp.msg)
```

## 3. 常用 API

### 3.1 获取项目列表

```python
resp = dida.get_projects()
projects = resp.data if resp.code == 0 else []
```

### 3.2 获取任务列表（返回迭代器）

`task_list` 返回 `Iterator[Task]`，推荐转为 `list` 使用。

```python
project_id = "YOUR_PROJECT_ID"
tasks = list(dida.task_list(project_id=project_id, enhancement=True))
```

- `enhancement=True`: 使用 cookie 端点（`/api/v2/...`）
- `enhancement=False`: 使用 open API 端点（`/open/v1/...`）

### 3.3 创建任务

```python
from datetime import datetime, timedelta

resp = dida.task_create(
    project_id="YOUR_PROJECT_ID",
    title="测试任务",
    content="这是一个测试任务",
    tags=["L-测试"],
    priority=3,
    start_date=datetime.utcnow() + timedelta(minutes=1),
    reminder=True,
)
```

### 3.4 更新任务

```python
resp = dida.task_update(
    project_id="YOUR_PROJECT_ID",
    task_id="YOUR_TASK_ID",
    content="补充说明",
    content_front=False,
)
```

### 3.5 完成任务

```python
resp = dida.task_complete(
    project_id="YOUR_PROJECT_ID",
    task_id="YOUR_TASK_ID",
)
```

### 3.6 其他查询接口

```python
task_resp = dida.task_get(project_id="YOUR_PROJECT_ID", task_id="YOUR_TASK_ID")
comment_resp = dida.task_comments(project_id="YOUR_PROJECT_ID", task_id="YOUR_TASK_ID")
```

## 4. 可靠性行为说明

- 超时：所有请求走统一 timeout（默认 3 秒）
- 重试：最多 3 次，指数退避；429/5xx/网络异常会重试，普通 4xx 不重试
- 幂等写入：`task_create` / `task_update` / `task_complete` 在 TTL 窗口内用幂等键去重
- 日志：记录 `task_id / target / result / duration_ms`，不输出 secrets

## 5. Live 测试

live 测试文件：

- `tests/live/test_dida365_live.py`

启动脚本（仅运行 dida live 测试，不会带上 feishu live）：

```bash
python3 tests/live/run_dida365_live.py
```

启用写链路测试（创建 -> 更新 -> 完成）：

```bash
python3 tests/live/run_dida365_live.py --write
```

使用 env 文件：

```bash
python3 tests/live/run_dida365_live.py --env-file /path/to/.env.live
```

透传 pytest 参数（例如只跑某个用例）：

```bash
python3 tests/live/run_dida365_live.py -k get_projects
```

必需环境变量：

- `DIDA_ACCESS_TOKEN`
- `DIDA_COOKIE`
- `DIDA_PROJECT_ID`
