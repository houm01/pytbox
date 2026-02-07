# AGENTS.md
This file contains the highest-priority rules for AI. All changes must follow it.

================================================
## GLOBAL RULES

MUST:
- Make small, incremental changes
- Keep backward compatibility
- New/modified code must include pytest coverage
- Use type hints
- Classes and functions must have Google-style docstrings

MUST NOT:
- Perform large-scale refactors
- Change public APIs
- Delete tests
- Introduce heavy dependencies
- Use `print` for debugging
- except: pass
================================================

## RETURN RULES (CRITICAL)

External IO (network/API/DB/files/external systems):
→ MUST return ReturnResponse
(src/pytbox/schemas/response.py)

Pure functions (no side effects):
→ May return raw values directly

FORBIDDEN:
- Mixing ReturnResponse and raw values at the same abstraction layer

## RELIABILITY RULES (OPS REQUIRED)

All external calls must include:
- timeout
- retry ≤ 3 (exponential backoff)
- idempotent writes

Required:
- Re-runnable without side effects
- Key-step logging (task_id/target/result/duration)
- Do not log secrets

## TESTING
Required:
- Every public function must have tests
- Mock external dependencies
- No real network access

## WORKFLOW (REQUIRED)
Before changing code, you must:
1. Read AGENTS.md
2. List files to be modified + risks + test plan
3. Wait for confirmation before implementation

After completion, you must output:
- changed files
- how to verify
- risks / rollback
