# 01 - Return Contract

## Goal (MUST)
- 所有 Feishu 外部 IO（HTTP/API 调用）对外统一返回 `ReturnResponse`：
  `src/pytbox/schemas/response.py::ReturnResponse`
- 保持对外行为兼容：现有调用方不因重构而崩（允许先加 wrapper 过渡）

## Non-Goals (MUST NOT)
- 不在此阶段统一 HTTP 栈/重写 auth（留到后续子 spec）
- 不大规模改模块结构

## Current Issues
- client.request() 返回 FeishuResponse（dataclass），endpoints 部分返回 ReturnResponse/部分返回 FeishuResponse，存在混用。

## Design
- 新增/调整一层“适配器”，将 FeishuResponse -> ReturnResponse（或直接让 request 返回 ReturnResponse）
- 统一错误表达：
  - code：0 成功；非 0 失败（保留现有项目约定，如有）
  - message：简短描述
  - data：业务数据（dict/列表/原始结构）
  - error（可选）：包含 http_status/errcode/errmsg/req_id

## Acceptance Criteria (AC)
- AC1: Feishu 模块对外暴露的所有“会打飞书 API”的函数返回 ReturnResponse
- AC2: 不再出现同层混用（同一抽象层要么全 ReturnResponse，要么纯工具裸返回）
- AC3: 保留旧接口/导入路径（如必须改变，需提供兼容 wrapper）

## Tests
- mock HTTP 响应：success / 4xx / 5xx / timeout
- 验证：返回类型为 ReturnResponse；code/message/data 字段符合预期
