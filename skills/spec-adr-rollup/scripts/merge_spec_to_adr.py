#!/usr/bin/env python3
"""Merge spec markdown files into a single ADR markdown document."""

from __future__ import annotations

import argparse
import logging
import re
import sys
import time
import uuid
from datetime import date
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

# Ensure local `src/` imports work when script is run from repository root.
REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pytbox.schemas.codes import RespCode
from pytbox.schemas.response import ReturnResponse

LOGGER = logging.getLogger("spec_adr_rollup")
if not LOGGER.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

_RETRY_DELAYS: Sequence[float] = (0.0, 0.2, 0.4)
_REFERENCE_PATTERN = re.compile(r"([A-Za-z0-9][A-Za-z0-9._/-]*\.md)")
_CHILD_SPEC_PATTERN = re.compile(r"^\d{2,}[-_].+\.md$")


def _log_step(task_id: str, target: str, result: str, duration: float) -> None:
    LOGGER.info(
        "task_id=%s target=%s result=%s duration=%.3fs",
        task_id,
        target,
        result,
        duration,
    )


def _read_text_with_retry(path: Path, task_id: str) -> ReturnResponse:
    start = time.monotonic()
    last_error: Optional[str] = None
    for delay in _RETRY_DELAYS:
        if delay > 0:
            time.sleep(delay)
        try:
            content = path.read_text(encoding="utf-8")
            _log_step(task_id, str(path), "read_ok", time.monotonic() - start)
            return ReturnResponse.ok(data={"content": content}, msg="read success")
        except Exception as exc:  # noqa: BLE001 - convert all file errors to response
            last_error = str(exc)
    _log_step(task_id, str(path), "read_fail", time.monotonic() - start)
    return ReturnResponse.fail(
        code=RespCode.INTERNAL_ERROR,
        msg="read failed",
        data={"path": str(path), "error": last_error},
    )


def _write_text_with_retry(path: Path, content: str, task_id: str) -> ReturnResponse:
    start = time.monotonic()
    last_error: Optional[str] = None
    for delay in _RETRY_DELAYS:
        if delay > 0:
            time.sleep(delay)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            _log_step(task_id, str(path), "write_ok", time.monotonic() - start)
            return ReturnResponse.ok(data={"path": str(path)}, msg="write success")
        except Exception as exc:  # noqa: BLE001 - convert all file errors to response
            last_error = str(exc)
    _log_step(task_id, str(path), "write_fail", time.monotonic() - start)
    return ReturnResponse.fail(
        code=RespCode.INTERNAL_ERROR,
        msg="write failed",
        data={"path": str(path), "error": last_error},
    )


def _extract_markdown_refs(spec_text: str) -> List[str]:
    refs: List[str] = []
    seen = set()
    for match in _REFERENCE_PATTERN.findall(spec_text):
        name = match.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        refs.append(name)
    return refs


def _is_child_spec_candidate(ref_name: str, existing_md_files: Sequence[str]) -> bool:
    if ref_name in existing_md_files:
        return True
    return bool(_CHILD_SPEC_PATTERN.match(ref_name))


def _resolve_targets(spec_dir: Path, task_id: str) -> ReturnResponse:
    spec_entry = spec_dir / "spec.md"
    md_files = sorted([item.name for item in spec_dir.glob("*.md")])

    if not md_files:
        _log_step(task_id, str(spec_dir), "no_markdown", 0.0)
        return ReturnResponse.fail(
            code=RespCode.INVALID_PARAMS,
            msg="no markdown files found",
            data={"spec_dir": str(spec_dir)},
        )

    ordered_targets: List[str] = []
    if spec_entry.exists():
        ordered_targets.append("spec.md")
        spec_resp = _read_text_with_retry(spec_entry, task_id)
        if spec_resp.code != int(RespCode.OK):
            return spec_resp
        ref_names = _extract_markdown_refs(str(spec_resp.data.get("content", "")))
        for ref_name in ref_names:
            if ref_name == "spec.md":
                continue
            if not _is_child_spec_candidate(ref_name, md_files):
                continue
            if ref_name not in ordered_targets:
                ordered_targets.append(ref_name)

    for md_name in md_files:
        if md_name not in ordered_targets:
            ordered_targets.append(md_name)

    _log_step(task_id, str(spec_dir), "resolve_targets_ok", 0.0)
    return ReturnResponse.ok(data={"targets": ordered_targets}, msg="resolve targets success")


def _render_adr_markdown(
    spec_dir: Path,
    generated_on: date,
    statuses: Sequence[Tuple[str, str, str, str]],
    merged_sections: Sequence[str],
) -> str:
    source_dir = spec_dir.as_posix()
    lines: List[str] = [
        "# ADR - {}".format(spec_dir.name),
        "",
        "- Source: `{}`".format(source_dir),
        "- Generated On: `{}`".format(generated_on.isoformat()),
        "",
        "## Merge Status",
        "",
        "| File | Status | Date | Note |",
        "| --- | --- | --- | --- |",
    ]

    for file_name, status, status_date, note in statuses:
        lines.append("| {} | {} | {} | {} |".format(file_name, status, status_date, note))

    lines.extend(["", "## Merged Content", ""])
    lines.extend(merged_sections)
    lines.append("")
    return "\n".join(lines)


def merge_spec_to_adr(
    spec_dir: Path,
    adr_root: Optional[Path] = None,
    run_date: Optional[date] = None,
) -> ReturnResponse:
    """Merge a spec directory into a single ADR markdown file."""
    task_id = "spec-adr-rollup-{}".format(uuid.uuid4().hex[:8])
    started_at = time.monotonic()

    resolved_spec_dir = spec_dir.resolve()
    if not resolved_spec_dir.exists() or not resolved_spec_dir.is_dir():
        _log_step(task_id, str(spec_dir), "invalid_spec_dir", time.monotonic() - started_at)
        return ReturnResponse.fail(
            code=RespCode.INVALID_PARAMS,
            msg="spec_dir is invalid",
            data={"spec_dir": str(spec_dir)},
        )

    status_date = (run_date or date.today()).isoformat()
    target_resp = _resolve_targets(resolved_spec_dir, task_id)
    if target_resp.code != int(RespCode.OK):
        return target_resp

    targets = list(target_resp.data.get("targets", []))
    spec_root = resolved_spec_dir

    statuses: List[Tuple[str, str, str, str]] = []
    merged_sections: List[str] = []
    done_count = 0

    for rel_name in targets:
        candidate = (spec_root / rel_name).resolve()
        try:
            candidate.relative_to(spec_root)
        except ValueError:
            statuses.append((rel_name, "放弃", status_date, "Reference escapes spec directory"))
            continue

        if not candidate.exists() or not candidate.is_file():
            statuses.append((rel_name, "放弃", status_date, "File not found"))
            continue

        read_resp = _read_text_with_retry(candidate, task_id)
        if read_resp.code != int(RespCode.OK):
            statuses.append((rel_name, "放弃", status_date, "Read failed"))
            continue

        content = str(read_resp.data.get("content", "")).strip()
        statuses.append((rel_name, "Done", status_date, "Merged"))
        merged_sections.append("### {}\n\n{}\n".format(rel_name, content))
        done_count += 1

    output_root = (adr_root or Path("docs/adr")).resolve()
    output_path = output_root / "{}.md".format(spec_root.name)

    merged_doc = _render_adr_markdown(spec_root, run_date or date.today(), statuses, merged_sections)
    write_resp = _write_text_with_retry(output_path, merged_doc, task_id)
    if write_resp.code != int(RespCode.OK):
        return write_resp

    _log_step(task_id, str(output_path), "merge_done", time.monotonic() - started_at)
    return ReturnResponse.ok(
        data={
            "output_path": str(output_path),
            "done_count": done_count,
            "skipped_count": len(statuses) - done_count,
        },
        msg="merged spec to adr",
    )


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge spec docs into docs/adr markdown")
    parser.add_argument("--spec-dir", required=True, help="Spec directory (e.g., docs/specs/2026-02-feishu)")
    parser.add_argument("--adr-root", default="docs/adr", help="ADR root directory")
    return parser.parse_args(argv)


def _main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    response = merge_spec_to_adr(spec_dir=Path(args.spec_dir), adr_root=Path(args.adr_root))
    if response.code != int(RespCode.OK):
        LOGGER.error("merge failed: %s", response.msg)
        return 1
    LOGGER.info("merge finished: %s", response.data)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
