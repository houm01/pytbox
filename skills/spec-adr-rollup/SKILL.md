---
name: spec-adr-rollup
description: Merge a spec entry file (`spec.md`) and child spec markdown files into one ADR document under `docs/adr`, with per-file status (`Done` or `放弃`) and date. Use when the user asks to consolidate `docs/specs/<name>` into a single reviewable ADR output.
---

# Spec ADR Rollup

## Overview

Consolidate one spec folder into one ADR markdown file with a deterministic status table.

## Workflow

1. Identify the spec directory, usually `docs/specs/<spec-name>`.
2. Run the merge script:

```bash
python skills/spec-adr-rollup/scripts/merge_spec_to_adr.py --spec-dir docs/specs/<spec-name> --adr-root docs/adr
```

3. Confirm output exists at `docs/adr/<spec-name>.md`.
4. Verify the status table:
- `Done (YYYY-MM-DD)`: file exists and is merged.
- `放弃 (YYYY-MM-DD)`: file missing, unreadable, or unsafe path.

## Notes

- Keep execution idempotent: reruns overwrite the same ADR file.
- Preserve merge order: `spec.md` first, then referenced child docs, then remaining markdown files.
- Avoid logging secrets.

## Script

- `scripts/merge_spec_to_adr.py`: merges spec docs and writes one ADR markdown.
