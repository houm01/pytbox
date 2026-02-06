# Feishu Refactor Spec (Entry)

本次重构拆分为 3 个小 spec，按顺序执行，逐个闭环：

1) 01-return-contract.md
- 统一返回为 ReturnResponse（外部 IO 必须）
- 先做 wrapper/适配，保持兼容

2) 02-http-client-unification.md
- 统一 HTTP 栈（建议全部走 httpx）
- 统一 timeout / retry / 错误映射 / 日志

3) 03-auth-token-cache.md
- 统一 token 获取/刷新/缓存
- 移除 print/env 乱写，提升可控性与可测试性

全局约束：
- 必须遵守 AGENTS.md
- 小步改动，保持兼容（除非子 spec 明确列出 breaking change）
- 每个子 spec 都必须有 pytest 覆盖（mock 外部请求）
