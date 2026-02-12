#!/usr/bin/env python3

"""Tests for publish.sh tag-only workflow."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLISH_SCRIPT_SOURCE = REPO_ROOT / "publish.sh"
ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def _run_command(
    args: list[str],
    cwd: Path,
    env: Optional[Dict[str, str]] = None,
    input_text: Optional[str] = None,
) -> subprocess.CompletedProcess[str]:
    """Run shell command and return CompletedProcess.

    Args:
        args: Command args.
        cwd: Working directory.
        env: Optional process env.
        input_text: Optional stdin text.

    Returns:
        subprocess.CompletedProcess[str]: Command execution result.
    """
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def _init_publish_repo(tmp_path: Path) -> Path:
    """Create isolated git repo with origin and publish.sh.

    Args:
        tmp_path: Pytest temp path.

    Returns:
        Path: Path to initialized git repo.
    """
    remote_path = tmp_path / "remote.git"
    repo_path = tmp_path / "repo"

    _run_command(["git", "init", "--bare", str(remote_path)], cwd=tmp_path)
    _run_command(["git", "init", str(repo_path)], cwd=tmp_path)

    _run_command(["git", "config", "user.name", "tester"], cwd=repo_path)
    _run_command(["git", "config", "user.email", "tester@example.com"], cwd=repo_path)

    (repo_path / "README.md").write_text("init\n", encoding="utf-8")
    _run_command(["git", "add", "README.md"], cwd=repo_path)
    _run_command(["git", "commit", "-m", "init"], cwd=repo_path)

    _run_command(["git", "branch", "-M", "main"], cwd=repo_path)
    _run_command(["git", "remote", "add", "origin", str(remote_path)], cwd=repo_path)
    _run_command(["git", "push", "-u", "origin", "main"], cwd=repo_path)

    target_script = repo_path / "publish.sh"
    shutil.copy2(PUBLISH_SCRIPT_SOURCE, target_script)
    target_script.chmod(0o755)
    return repo_path


def _run_publish_script(
    repo_path: Path,
    args: list[str],
    today: str,
    input_text: Optional[str] = None,
) -> subprocess.CompletedProcess[str]:
    """Run publish.sh under fixed date.

    Args:
        repo_path: Target repo path.
        args: publish.sh args.
        today: Fixed YYYYMMDD date for deterministic tests.
        input_text: Optional stdin input.

    Returns:
        subprocess.CompletedProcess[str]: Script result.
    """
    env = dict(os.environ)
    env["PUBLISH_DATE_OVERRIDE"] = today
    return _run_command(
        ["bash", str(repo_path / "publish.sh"), *args],
        cwd=repo_path,
        env=env,
        input_text=input_text,
    )


def _strip_ansi(value: str) -> str:
    """Strip ANSI color codes from text.

    Args:
        value: Raw console output.

    Returns:
        str: Text without ANSI control codes.
    """
    return ANSI_PATTERN.sub("", value)


def _list_local_tags(repo_path: Path) -> str:
    """Get local tags list.

    Args:
        repo_path: Target repo path.

    Returns:
        str: Newline-separated tag list.
    """
    result = _run_command(["git", "tag", "-l"], cwd=repo_path)
    return result.stdout.strip()


def _remote_has_tag(repo_path: Path, tag: str) -> bool:
    """Check whether origin has the given tag.

    Args:
        repo_path: Target repo path.
        tag: Tag name.

    Returns:
        bool: True when remote includes the tag.
    """
    result = _run_command(["git", "ls-remote", "--tags", "origin", tag], cwd=repo_path)
    return bool(result.stdout.strip())


def _head_commit(repo_path: Path) -> str:
    """Return current HEAD commit hash.

    Args:
        repo_path: Target repo path.

    Returns:
        str: HEAD hash.
    """
    result = _run_command(["git", "rev-parse", "HEAD"], cwd=repo_path)
    return result.stdout.strip()


def test_publish_auto_first_tag_with_confirmation(tmp_path: Path) -> None:
    """Auto mode should create first tag after confirmation."""
    repo_path = _init_publish_repo(tmp_path)
    before_head = _head_commit(repo_path)

    result = _run_publish_script(repo_path, args=[], today="20260212", input_text="y\n")
    output = _strip_ansi(result.stdout + result.stderr)

    assert result.returncode == 0
    assert "目标标签: v0.0.1-20260212" in output
    assert "模式: auto" in output
    assert "v0.0.1-20260212" in _list_local_tags(repo_path)
    assert _remote_has_tag(repo_path, "v0.0.1-20260212")
    assert _head_commit(repo_path) == before_head


def test_publish_auto_carry_from_009_to_011(tmp_path: Path) -> None:
    """Auto mode should carry 0.0.9 to 0.1.1."""
    repo_path = _init_publish_repo(tmp_path)
    _run_command(["git", "tag", "-a", "v0.0.9-20260211", "-m", "v0.0.9-20260211"], cwd=repo_path)
    _run_command(["git", "push", "origin", "v0.0.9-20260211"], cwd=repo_path)

    result = _run_publish_script(repo_path, args=["--yes"], today="20260212")
    output = _strip_ansi(result.stdout + result.stderr)

    assert result.returncode == 0
    assert "目标标签: v0.1.1-20260212" in output
    assert "v0.1.1-20260212" in _list_local_tags(repo_path)


def test_publish_auto_carry_from_099_to_111(tmp_path: Path) -> None:
    """Auto mode should carry 0.9.9 to 1.1.1."""
    repo_path = _init_publish_repo(tmp_path)
    _run_command(["git", "tag", "-a", "v0.9.9-20260211", "-m", "v0.9.9-20260211"], cwd=repo_path)
    _run_command(["git", "push", "origin", "v0.9.9-20260211"], cwd=repo_path)

    result = _run_publish_script(repo_path, args=["--yes"], today="20260212")
    output = _strip_ansi(result.stdout + result.stderr)

    assert result.returncode == 0
    assert "目标标签: v1.1.1-20260212" in output
    assert "v1.1.1-20260212" in _list_local_tags(repo_path)


def test_publish_manual_tag_success_when_today(tmp_path: Path) -> None:
    """Manual tag should succeed when date equals today."""
    repo_path = _init_publish_repo(tmp_path)
    tag = "v1.2.3-20260212"

    result = _run_publish_script(repo_path, args=[tag, "--yes"], today="20260212")
    output = _strip_ansi(result.stdout + result.stderr)

    assert result.returncode == 0
    assert "模式: manual" in output
    assert tag in _list_local_tags(repo_path)
    assert _remote_has_tag(repo_path, tag)


def test_publish_manual_tag_fails_when_not_today(tmp_path: Path) -> None:
    """Manual tag should fail when date is not today."""
    repo_path = _init_publish_repo(tmp_path)
    result = _run_publish_script(
        repo_path,
        args=["v1.2.3-20260211", "--yes"],
        today="20260212",
    )
    output = _strip_ansi(result.stdout + result.stderr)

    assert result.returncode == 1
    assert "手动 tag 日期必须是当天 20260212" in output
    assert _list_local_tags(repo_path) == ""


def test_publish_cancel_when_not_confirmed(tmp_path: Path) -> None:
    """Script should exit without creating tag when confirmation declined."""
    repo_path = _init_publish_repo(tmp_path)
    result = _run_publish_script(repo_path, args=[], today="20260212", input_text="n\n")
    output = _strip_ansi(result.stdout + result.stderr)

    assert result.returncode == 0
    assert "已取消，未创建任何标签" in output
    assert _list_local_tags(repo_path) == ""


def test_publish_fails_when_tag_exists(tmp_path: Path) -> None:
    """Script should fail if target tag already exists."""
    repo_path = _init_publish_repo(tmp_path)
    existed_tag = "v0.0.1-20260212"
    _run_command(["git", "tag", "-a", existed_tag, "-m", existed_tag], cwd=repo_path)
    _run_command(["git", "push", "origin", existed_tag], cwd=repo_path)

    result = _run_publish_script(repo_path, args=[existed_tag, "--yes"], today="20260212")
    output = _strip_ansi(result.stdout + result.stderr)

    assert result.returncode == 1
    assert f"标签 {existed_tag} 已存在" in output
