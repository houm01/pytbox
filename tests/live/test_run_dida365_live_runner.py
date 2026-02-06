#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

import pytest


def _load_runner_module() -> Any:
    runner_path = Path(__file__).with_name("run_dida365_live.py")
    spec = importlib.util.spec_from_file_location("run_dida365_live", runner_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load run_dida365_live.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_env_file_parses_lines(tmp_path: Path) -> None:
    module = _load_runner_module()
    env_file = tmp_path / ".env.live"
    env_file.write_text(
        "# comment\n"
        "DIDA_ACCESS_TOKEN=token_value\n"
        "DIDA_COOKIE='cookie_value'\n"
        "INVALID_LINE\n",
        encoding="utf-8",
    )

    env_map = module.load_env_file(str(env_file))

    assert env_map["DIDA_ACCESS_TOKEN"] == "token_value"
    assert env_map["DIDA_COOKIE"] == "cookie_value"
    assert "INVALID_LINE" not in env_map


def test_build_pytest_cmd_contains_live_flags() -> None:
    module = _load_runner_module()
    cmd = module.build_pytest_cmd(["-k", "get_projects"])

    assert cmd[0] == module.sys.executable
    assert "--run-live" in cmd
    assert "tests/live/test_dida365_live.py" in cmd
    assert "-m" in cmd
    assert "live" in cmd
    assert "-k" in cmd


def test_main_returns_1_when_required_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_runner_module()
    for key in module.REQUIRED_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)

    rc = module.main([])
    assert rc == 1


def test_main_sets_write_flag_and_runs_pytest(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_runner_module()
    monkeypatch.setenv("DIDA_ACCESS_TOKEN", "token")
    monkeypatch.setenv("DIDA_COOKIE", "cookie")
    monkeypatch.setenv("DIDA_PROJECT_ID", "project")
    monkeypatch.delenv("DIDA_LIVE_ALLOW_WRITE", raising=False)

    captured: dict[str, Any] = {}

    def fake_run(cmd: list[str], check: bool, env: dict[str, str]):
        captured["cmd"] = cmd
        captured["check"] = check
        captured["env"] = env

        class Completed:
            returncode = 0

        return Completed()

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    rc = module.main(["--write", "-k", "get_projects"])

    assert rc == 0
    assert captured["check"] is False
    assert "--run-live" in captured["cmd"]
    assert captured["env"]["DIDA_LIVE_ALLOW_WRITE"] == "1"


def test_apply_env_defaults_does_not_override_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_runner_module()
    monkeypatch.setenv("DIDA_COOKIE", "existing_cookie")

    module.apply_env_defaults(
        {
            "DIDA_COOKIE": "new_cookie",
            "DIDA_PROJECT_ID": "project_from_file",
        }
    )

    assert os.getenv("DIDA_COOKIE") == "existing_cookie"
    assert os.getenv("DIDA_PROJECT_ID") == "project_from_file"
