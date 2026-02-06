#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Mapping, Sequence


REQUIRED_ENV_KEYS = (
    "DIDA_ACCESS_TOKEN",
    "DIDA_COOKIE",
    "DIDA_PROJECT_ID",
)

def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Dida365 live tests safely (opt-in)."
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=None,
        help="Optional env file path (KEY=VALUE per line).",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Enable write flow test (create/update/complete).",
    )
    args, pytest_args = parser.parse_known_args(argv)
    args.pytest_args = pytest_args
    return args


def load_env_file(path: str) -> dict[str, str]:
    env_map: dict[str, str] = {}
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key:
            env_map[key] = value
    return env_map


def apply_env_defaults(defaults: Mapping[str, str]) -> None:
    for key, value in defaults.items():
        if key not in os.environ:
            os.environ[key] = value


def collect_missing_env(required_keys: Sequence[str]) -> list[str]:
    return [key for key in required_keys if not os.getenv(key)]


def build_pytest_cmd(extra_args: Sequence[str] | None = None) -> list[str]:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "tests/live/test_dida365_live.py",
        "--run-live",
        "-m",
        "live",
    ]
    if extra_args:
        cmd.extend(extra_args)
    return cmd


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    if args.env_file:
        env_defaults = load_env_file(args.env_file)
        apply_env_defaults(env_defaults)

    missing_keys = collect_missing_env(REQUIRED_ENV_KEYS)
    if missing_keys:
        keys = ", ".join(missing_keys)
        print(f"Missing required env vars: {keys}")
        print(
            "Required: DIDA_ACCESS_TOKEN, DIDA_COOKIE, DIDA_PROJECT_ID. "
            "Use --env-file or export them first."
        )
        return 1

    if args.write:
        os.environ["DIDA_LIVE_ALLOW_WRITE"] = "1"

    cmd = build_pytest_cmd(args.pytest_args)
    run = subprocess.run(cmd, check=False, env=os.environ.copy())
    return run.returncode


if __name__ == "__main__":
    raise SystemExit(main())
