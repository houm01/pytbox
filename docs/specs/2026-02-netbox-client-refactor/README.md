# Netbox Client Refactor Spec (2026-02)

## Summary
- 目标：在不改 public API 的前提下，重构 `src/pytbox/netbox/client.py`，降低维护成本并提升稳定性。
- 原则：小步改造、向后兼容、每步可回滚。
- 本 spec 为精简执行版，不引入大而全的模板。

## Scope
- In:
  - 拆分重复逻辑（查询 ID、构造 payload、请求发送、错误处理）
  - 统一外部 IO 返回契约（`ReturnResponse`）
  - 统一超时、重试（<=3，指数退避）、关键日志
  - 补齐/修正 pytest（全 mock，无真实网络）
- Out:
  - 调整 NetBox 业务字段语义
  - 重命名或删除现有 public 方法
  - 一次性大重构

## Current Problems
- 单文件过大（~1700+ 行，50+ 方法），职责混杂。
- 存在重复定义（如 `get_tenants_id`、`get_site_id`）。
- 返回结构不一致（`msg/message` 混用，部分方法行为不统一）。
- 外部调用分散，缺少统一 retry/日志策略。

## Refactor Plan
1. 第 1 步：收敛请求层
- 新增内部私有请求助手（仅内部调用），统一 `timeout/retry/error mapping`。
- 保持现有 public 方法签名不变。

2. 第 2 步：收敛返回层
- 所有外部 IO 方法统一返回 `ReturnResponse(code, msg, data)`。
- 兼容旧字段时，仅在内部做适配，不向外扩散双标准。

3. 第 3 步：去重与模块内聚
- 抽取重复的 `get_*_id` 查询逻辑与 payload 清理逻辑。
- 修复重复定义函数，保留一个权威实现。

4. 第 4 步：可观测性与稳定性
- 增加关键步骤日志：`task_id/target/result/duration`。
- 日志脱敏，禁止输出 token 等敏感信息。

## Compatibility Rules
- 不改 public 类名/方法名/参数语义。
- 调用方可按原方式调用，不需要迁移。
- 如需新增能力，只允许新增可选参数并提供默认值。

## Test Plan
- 覆盖范围：每个 public 方法至少 1 个测试。
- 全量 mock：`requests` / `pynetbox` 外部依赖。
- 覆盖场景：
  - 成功、4xx、5xx、timeout
  - retry 次数与退避行为
  - 返回类型与关键字段一致性
  - 幂等写入（重复执行无副作用）

## Rollout / Backout
- Rollout：按“请求层 -> 返回层 -> 去重 -> 日志/稳定性”分 PR 合入。
- Backout：按 PR 粒度回滚，不影响已验证步骤。
