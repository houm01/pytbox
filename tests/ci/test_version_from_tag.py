#!/usr/bin/env python3

"""Tests for CI release tag version conversion."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ci" / "version_from_tag.py"


def _load_module() -> ModuleType:
    """Load version_from_tag script module for direct unit tests.

    Returns:
        ModuleType: Loaded module instance.
    """
    module_spec = importlib.util.spec_from_file_location("version_from_tag", SCRIPT_PATH)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError("failed to load version_from_tag module")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    return module


MODULE = _load_module()


def test_parse_release_tag_with_date() -> None:
    """Date style tag should map to post-release PEP440 version."""
    parsed = MODULE.parse_release_tag("v0.7.5-20260212")

    assert parsed.major == 0
    assert parsed.minor == 7
    assert parsed.patch == 5
    assert parsed.date == "20260212"
    assert parsed.pep440_version == "0.7.5.post20260212"


def test_parse_release_tag_without_date() -> None:
    """Simple semver tag should keep base PEP440 version."""
    parsed = MODULE.parse_release_tag("v1.2.3")

    assert parsed.major == 1
    assert parsed.minor == 2
    assert parsed.patch == 3
    assert parsed.date is None
    assert parsed.pep440_version == "1.2.3"


def test_parse_release_tag_rejects_invalid_format() -> None:
    """Unsupported tag format should raise ValueError."""
    with pytest.raises(ValueError, match="unsupported tag format"):
        MODULE.parse_release_tag("release-1.2.3")


def test_parse_release_tag_rejects_invalid_date() -> None:
    """Invalid calendar date should raise ValueError."""
    with pytest.raises(ValueError, match="invalid date in tag"):
        MODULE.parse_release_tag("v1.2.3-20260230")


def test_update_pyproject_version_updates_once(tmp_path: Path) -> None:
    """Version field should be updated exactly once."""
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        '[project]\nname = "pytbox"\nversion = "0.7.3"\n',
        encoding="utf-8",
    )

    MODULE.update_pyproject_version(pyproject_path, "0.7.5.post20260212")
    content = pyproject_path.read_text(encoding="utf-8")

    assert 'version = "0.7.5.post20260212"' in content
    assert 'version = "0.7.3"' not in content


def test_update_pyproject_version_raises_when_missing(tmp_path: Path) -> None:
    """Missing version line should raise ValueError."""
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text('[project]\nname = "pytbox"\n', encoding="utf-8")

    with pytest.raises(ValueError, match="failed to locate version field"):
        MODULE.update_pyproject_version(pyproject_path, "0.7.5")


def test_main_updates_pyproject_and_exports_env(tmp_path: Path) -> None:
    """CLI should update pyproject and write PACKAGE_VERSION to env file."""
    pyproject_path = tmp_path / "pyproject.toml"
    env_path = tmp_path / "github_env.txt"
    pyproject_path.write_text(
        '[project]\nname = "pytbox"\nversion = "0.7.3"\n',
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--tag",
            "v0.7.5-20260212",
            "--pyproject",
            str(pyproject_path),
            "--github-env",
            str(env_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert 'version = "0.7.5.post20260212"' in pyproject_path.read_text(encoding="utf-8")
    assert "PACKAGE_VERSION=0.7.5.post20260212" in env_path.read_text(encoding="utf-8")
