#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

import pytest


def _load_runner_module() -> Any:
    runner_path = Path(__file__).with_name("run_feishu_live.py")
    spec = importlib.util.spec_from_file_location("run_feishu_live", runner_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load run_feishu_live.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_env_file_parses_lines(tmp_path: Path) -> None:
    module = _load_runner_module()
    env_file = tmp_path / ".env.live"
    env_file.write_text(
        "# comment\n"
        "FEISHU_APP_ID=app_id\n"
        "FEISHU_APP_SECRET='app_secret'\n"
        "INVALID_LINE\n",
        encoding="utf-8",
    )

    env_map = module.load_env_file(str(env_file))

    assert env_map["FEISHU_APP_ID"] == "app_id"
    assert env_map["FEISHU_APP_SECRET"] == "app_secret"
    assert "INVALID_LINE" not in env_map


def test_build_pytest_cmd_contains_live_flags() -> None:
    module = _load_runner_module()
    cmd = module.build_pytest_cmd(["-k", "token"])

    assert cmd[0] == module.sys.executable
    assert "--run-live" in cmd
    assert "tests/live/test_feishu_live.py" in cmd
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
    monkeypatch.setenv("FEISHU_APP_ID", "app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "secret")
    monkeypatch.delenv("FEISHU_LIVE_ALLOW_WRITE", raising=False)

    captured: dict[str, Any] = {}

    def fake_run(cmd: list[str], check: bool, env: dict[str, str]):
        captured["cmd"] = cmd
        captured["check"] = check
        captured["env"] = env

        class Completed:
            returncode = 0

        return Completed()

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    rc = module.main(["--write", "-k", "token"])

    assert rc == 0
    assert captured["check"] is False
    assert "--run-live" in captured["cmd"]
    assert captured["env"]["FEISHU_LIVE_ALLOW_WRITE"] == "1"


def test_apply_env_defaults_does_not_override_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_runner_module()
    monkeypatch.setenv("FEISHU_APP_ID", "existing_app")

    module.apply_env_defaults(
        {
            "FEISHU_APP_ID": "new_app",
            "FEISHU_APP_SECRET": "secret_from_file",
        }
    )

    assert os.getenv("FEISHU_APP_ID") == "existing_app"
    assert os.getenv("FEISHU_APP_SECRET") == "secret_from_file"
