# Feishu 使用文档

本文档说明 `pytbox` 中 Feishu 客户端的初始化、常用调用方式、返回契约，以及 live 测试运行方法。

## 1. 初始化

```python
from pytbox.feishu.client import Client

feishu = Client(
    app_id="YOUR_FEISHU_APP_ID",
    app_secret="YOUR_FEISHU_APP_SECRET",
)
```

## 2. 返回契约

所有外部 IO 方法统一返回 `src/pytbox/schemas/response.py::ReturnResponse`：

- `code`: `0` 表示成功，非 `0` 表示失败
- `msg`: 状态描述
- `data`: 业务数据

建议统一判断：

```python
resp = feishu.auth.get_tenant_access_token()
if resp.code != 0:
    raise RuntimeError(resp.msg)
```

## 3. 常用 API（真实调用示例）

### 3.1 获取 tenant access token

```python
resp = feishu.auth.get_tenant_access_token()
if resp.code == 0:
    token = resp.data["token"]
    expires_at = resp.data["expires_at"]
else:
    raise RuntimeError(resp.msg)
```

### 3.2 发送文本消息

```python
resp = feishu.message.send_text(
    text="hello from pytbox",
    receive_id="ou_xxx",  # open_id
)
if resp.code != 0:
    raise RuntimeError(resp.msg)
```

### 3.3 发送卡片模板消息

```python
resp = feishu.message.send_card(
    template_id="AAqzcy5Qrx84H",
    template_variable={
        "color": "red",
        "title": "告警测试",
        "sub_title": "这是子标题",
        "priority": "P1",
        "content": "消息内容",
    },
    receive_id="ou_xxx",
)
if resp.code != 0:
    raise RuntimeError(resp.msg)
```

### 3.4 通过 webhook 发送卡片

```python
resp = feishu.message.webhook_send_feishu_card(
    webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/xxxx",
    template_id="AAqXPIkIOW0g9",
    template_variable={"event_name": "test"},
)
if resp.code != 0:
    raise RuntimeError(resp.msg)
```

## 4. Live 测试

live 测试文件：

- `tests/live/test_feishu_live.py`

运行脚本：

- `tests/live/run_feishu_live.py`

### 4.1 只跑读链路（推荐先跑）

```bash
PYTHONPATH=src .venv/bin/python tests/live/run_feishu_live.py
```

必需环境变量：

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`

### 4.2 跑写链路（发送消息）

```bash
PYTHONPATH=src .venv/bin/python tests/live/run_feishu_live.py --write
```

额外需要：

- `FEISHU_RECEIVE_ID`

### 4.3 使用 env 文件

```bash
PYTHONPATH=src .venv/bin/python tests/live/run_feishu_live.py --env-file /path/to/.env.live
```

### 4.4 透传 pytest 参数

```bash
PYTHONPATH=src .venv/bin/python tests/live/run_feishu_live.py -k token
```
