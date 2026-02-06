# 03 - Auth & Token Cache

## Goal (MUST)
- 统一 tenant_access_token 获取/刷新/缓存策略：
  - 单一来源、单一写入路径
  - 可测试、可控、可观测
- 禁止：
  - print
  - 随意写入 os.environ 作为持久缓存
- 日志不泄露 secret

## Non-Goals (MUST NOT)
- 不引入复杂分布式缓存（保持本地可用即可）
- 不改变配置注入方式（除非明确写出）

## Current Issues
- 使用 shelve /tmp/.feishu_token + 环境变量写入 + print 混用，行为不可预测。

## Design
- TokenProvider：
  - get_token() -> ReturnResponse(data={"token": "...", "expires_at": ...})
  - 缓存策略：内存优先，落盘可选（路径可配置）
  - 过期判断：提前 N 秒刷新（buffer）
- 并发/多进程：
  - 最小实现：简单文件锁或“失败可重试”的策略（按现状取舍）

## Acceptance Criteria (AC)
- AC1: 获取 token 只有一套逻辑入口（TokenProvider）
- AC2: 不再写 os.environ 作为缓存；不再出现 print
- AC3: token 过期可自动刷新；失败会返回 ReturnResponse 且日志可定位（不含 secret）

## Tests
- mock token API：首次获取、命中缓存、过期刷新、刷新失败
- 验证：不会把 token 写到日志/异常里（至少验证日志内容不包含 token 字符串）
