# Dida365 Refactor Spec (2026-02)

## Summary
- 在不改 public API 的前提下，重构 `src/pytbox/dida365.py`。
- 外部 IO 统一返回 `src/pytbox/schemas/response.py::ReturnResponse`。
- 增加 timeout、retry（<=3，指数退避）、写入幂等、关键日志与测试覆盖。

## Scope
- In:
  - `Dida365` 的请求入口统一与返回契约统一
  - `task_create/task_update/task_complete` 幂等
  - `task_list` 保持可迭代兼容
  - pytest 全 mock（禁真实网络）
- Out:
  - `alert/logger` 业务重构
  - 跨模块 HTTP 栈统一

## Public Interface
- 保持类和方法名不变：
  - `request`
  - `task_list`
  - `task_create`
  - `task_complete`
  - `task_get`
  - `task_comments`
  - `task_update`
  - `get_projects`
- 新增可选构造参数（兼容）：
  - `timeout=3`
  - `max_retries=3`
  - `retry_backoff_base=0.5`
  - `idempotency_ttl_seconds=300`

## Data Contract
- 外部 IO 返回：
  - `ReturnResponse(code, msg, data)`
- 约定：
  - `code == 0` 成功
  - `code != 0` 失败
- `task_list` 为兼容保留迭代器返回；真实 IO 在内部先收敛为 `ReturnResponse`。

## Observability
- 每次外部请求记录关键字段：
  - `task_id`
  - `target`
  - `result`
  - `duration_ms`
- 日志禁止输出 `token/cookie/Authorization` 明文。

## Test Plan
- 新增 `tests/test_dida365.py`，每个 public 方法至少 1 个测试。
- 全部 mock `requests.request`，覆盖：
  - success / 4xx / 5xx / timeout / 非 JSON
  - retry 次数与策略（5xx/429/网络异常重试，普通 4xx 不重试）
  - 幂等写入（重复请求只执行一次）
  - 返回类型与字段统一
  - 日志不含 secrets

## Rollout / Backout
- Rollout:
  - 先合入 `dida365.py` + 单测
  - 再观察调用方（`alert/logger`）行为
- Backout:
  - 回滚 `src/pytbox/dida365.py`
  - 移除 `tests/test_dida365.py`

## Assumptions / Defaults
- 默认重试 3 次，退避 0.5/1/2 秒。
- 幂等窗口 5 分钟（进程内缓存）。
- 优先保持历史调用方式可用（尤其 `task_list` 迭代）。
