# 测试方法说明

本文档说明 `pytbox` 的测试分层和推荐执行方式。

## 1. 测试分层

- 单元测试（默认）：`tests/` 下非 `tests/live/` 的测试
- Live 测试（显式开启）：`tests/live/` 下带 `@pytest.mark.live` 的测试

Live 测试默认不会执行，需要显式加 `--run-live`。

## 2. 单元测试

### 2.1 全量单元测试

```bash
python3 -m pytest -q
```

### 2.2 指定模块

```bash
python3 -m pytest -q tests/feishu
python3 -m pytest -q tests/test_feishu.py
```

说明：

- 单元测试必须 mock 外部依赖
- 单元测试禁止真实网络调用

## 3. Live 测试

仓库已有 live 测试门控实现：

- 文件：`tests/live/conftest.py`
- 开关：`--run-live`

### 3.1 Dida365 live

```bash
python3 tests/live/run_dida365_live.py
python3 tests/live/run_dida365_live.py --write
```

### 3.2 Feishu live

```bash
PYTHONPATH=src .venv/bin/python tests/live/run_feishu_live.py
PYTHONPATH=src .venv/bin/python tests/live/run_feishu_live.py --write
```

## 4. 直接用 pytest 跑 live

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/live --run-live -m live
```

只跑 Feishu live：

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/live/test_feishu_live.py --run-live -m live
```

## 5. 环境变量建议

- 推荐使用 `--env-file` 传入 live 凭据
- 写链路测试使用显式开关：`--write`
- 不要在日志、终端、提交记录中泄露 secrets
