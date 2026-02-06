# AGENTS.md
本文件是 AI 最高优先级规则。所有修改必须遵守。

================================================
## GLOBAL RULES

MUST:
- 小步修改
- 保持向后兼容
- 新增/修改必须有 pytest
- 使用 type hints
- 类和函数有 google 风格的 docstring

MUST NOT:
- 大规模重构
- 修改 public API
- 删除测试
- 引入重依赖
- print 调试
- except: pass
================================================

## RETURN RULES (CRITICAL)

外部 IO（网络/API/DB/文件/外部系统）:
→ MUST return ReturnResponse
(src/pytbox/schemas/response.py)

纯函数（无副作用）:
→ 可以直接返回原始值

FORBIDDEN:
- 同层混用 ReturnResponse 和 raw value

## RELIABILITY RULES (OPS REQUIRED)

所有外部调用必须：
- timeout
- retry ≤ 3（指数退避）
- 幂等写入

必须：
- 可重复执行不产生副作用
- 关键步骤日志（task_id/target/result/duration）
- 不记录 secrets

## TESTING
必须：
- 每个 public 函数有测试
- mock 外部依赖
- 禁止真实网络

## WORKFLOW (REQUIRED)
改代码前必须：
1. 阅读 AGENTS.md
2. 列出修改文件 + 风险 + 测试计划
3. 等确认后再实现

完成后必须输出：
- changed files
- how to verify
- risks / rollback