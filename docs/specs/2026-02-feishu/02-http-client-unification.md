# 02 - HTTP Client Unification

## Goal (MUST)
- Feishu 模块只保留一个 HTTP 实现（建议统一为 httpx）
- 所有外部请求必须：
  - timeout（默认值明确）
  - retry <= 3（指数退避）
  - 不重试：参数/权限类 4xx（429 可作为例外重试）
- 统一 URL 构造：禁止在 endpoint 里写死完整域名（统一 base_url + path）

## Non-Goals (MUST NOT)
- 不在本阶段改变业务 API 语义
- 不引入重依赖（如 tenacity 非必需则先不用）

## Current Issues
- endpoints.py 存在 requests.request + MultipartEncoder
- client.py 使用 httpx
- 部分接口使用绝对 URL/部分相对 path

## Design
- 抽象一个 `HttpClient`（可在现有 client.py 内实现）：
  - request(method, path, *, params/json/data/files/headers)
  - 统一 headers 注入（含 token）
  - 统一异常捕获与错误映射为 ReturnResponse
- Multipart 上传：
  - 若必须：用 httpx 的 files/data 方案实现
  - 不再直接调用 requests

## Acceptance Criteria (AC)
- AC1: Feishu 代码中不再直接使用 requests 发送 HTTP
- AC2: 所有请求都有 timeout；超时会触发 retry（最多 3 次）
- AC3: endpoint 不再硬编码域名；统一走 base_url

## Tests
- mock httpx client：验证 timeout/retry 行为（至少验证重试次数与最终结果）
- 覆盖：429/5xx 可重试，4xx 不重试（除 429）
