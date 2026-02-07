#!/usr/bin/env python3

"""Tests for network backup config loader."""

from __future__ import annotations

import json
from pathlib import Path

from pytbox.network.config_loader import load_backup_config


def test_load_backup_config_json_success(tmp_path: Path) -> None:
    """Load JSON config and normalize defaults."""
    config_path = tmp_path / "backup.json"
    config_payload = {
        "devices": [
            {
                "ip": "10.0.0.1",
                "os": "cisco",
                "protocol": "ssh",
                "username": "admin",
                "password": "secret",
            }
        ]
    }
    config_path.write_text(json.dumps(config_payload), encoding="utf-8")

    response = load_backup_config(str(config_path))

    assert response.code == 0
    assert response.data["output_dir"] == "./backups/network"
    assert response.data["timeout"] == 10
    assert response.data["retries"] == 3
    assert response.data["devices"][0]["port"] == 22


def test_load_backup_config_invalid_device_fields(tmp_path: Path) -> None:
    """Return error when device required fields are missing."""
    config_path = tmp_path / "backup.json"
    config_payload = {
        "devices": [
            {
                "ip": "10.0.0.1",
                "os": "cisco",
                "protocol": "ssh",
                "username": "admin",
            }
        ]
    }
    config_path.write_text(json.dumps(config_payload), encoding="utf-8")

    response = load_backup_config(str(config_path))

    assert response.code != 0
    assert "缺少字段" in response.msg


def test_load_backup_config_unsupported_extension(tmp_path: Path) -> None:
    """Reject unsupported config file extension."""
    config_path = tmp_path / "backup.conf"
    config_path.write_text("{}", encoding="utf-8")

    response = load_backup_config(str(config_path))

    assert response.code != 0
    assert "不支持的配置格式" in response.msg

