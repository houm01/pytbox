#!/usr/bin/env python3

"""Tests for network CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from click.testing import CliRunner

from pytbox.cli.main import main
from pytbox.schemas.response import ReturnResponse


class _FakeBackupService:
    """Fake backup service for CLI tests."""

    def __init__(
        self,
        captured_configs: List[Dict[str, Any]],
        response: ReturnResponse,
    ) -> None:
        """Initialize fake service.

        Args:
            captured_configs: Captured input configs.
            response: Expected response.
        """
        self._captured_configs = captured_configs
        self._response = response

    def backup_devices(self, config: Dict[str, Any]) -> ReturnResponse:
        """Capture config and return stub response.

        Args:
            config: Runtime backup config.

        Returns:
            ReturnResponse: Stubbed response.
        """
        self._captured_configs.append(config)
        return self._response


def test_network_backup_direct_mode_success_with_prompt(
    monkeypatch: Any,
) -> None:
    """Direct mode should prompt password when not provided."""
    captured_configs: List[Dict[str, Any]] = []
    fake_response = ReturnResponse.ok(
        data={"success_count": 1, "failed_count": 0, "success": [], "failed": []}
    )
    fake_service = _FakeBackupService(captured_configs, fake_response)
    monkeypatch.setattr(
        "pytbox.cli.network.commands.NetworkBackupService",
        lambda: fake_service,
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "network",
            "backup",
            "--os",
            "cisco",
            "--ip",
            "10.0.0.1",
            "--protocol",
            "ssh",
            "--username",
            "admin",
        ],
        input="prompt-secret\n",
    )

    assert result.exit_code == 0
    assert captured_configs[0]["devices"][0]["password"] == "prompt-secret"


def test_network_backup_direct_mode_missing_required_args() -> None:
    """Direct mode should fail when required args are incomplete."""
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "network",
            "backup",
            "--os",
            "huawei",
            "--ip",
            "10.0.0.2",
        ],
    )

    assert result.exit_code != 0
    assert "缺少参数" in result.output


def test_network_backup_config_mode_success(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    """Config mode should call backup service with loaded devices."""
    captured_configs: List[Dict[str, Any]] = []
    config_path = tmp_path / "devices.yml"
    config_path.write_text("devices: []", encoding="utf-8")

    monkeypatch.setattr(
        "pytbox.cli.network.commands.load_backup_config",
        lambda _path: ReturnResponse.ok(
            data={
                "output_dir": "./backups/network",
                "timeout": 10,
                "retries": 3,
                "devices": [
                    {
                        "ip": "10.0.0.10",
                        "os": "cisco",
                        "protocol": "ssh",
                        "username": "ops",
                        "password": "secret",
                    }
                ],
            }
        ),
    )

    fake_response = ReturnResponse.ok(
        data={"success_count": 1, "failed_count": 0, "success": [], "failed": []}
    )
    fake_service = _FakeBackupService(captured_configs, fake_response)
    monkeypatch.setattr(
        "pytbox.cli.network.commands.NetworkBackupService",
        lambda: fake_service,
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["network", "backup", "--config", str(config_path)],
    )

    assert result.exit_code == 0
    assert captured_configs[0]["devices"][0]["ip"] == "10.0.0.10"


def test_network_backup_config_plus_direct_overrides(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    """Direct args should override config fields when both provided."""
    captured_configs: List[Dict[str, Any]] = []
    config_path = tmp_path / "devices.yml"
    config_path.write_text("devices: []", encoding="utf-8")

    monkeypatch.setattr(
        "pytbox.cli.network.commands.load_backup_config",
        lambda _path: ReturnResponse.ok(
            data={
                "output_dir": "./backups/network",
                "timeout": 10,
                "retries": 3,
                "devices": [
                    {
                        "ip": "10.1.1.1",
                        "os": "huawei",
                        "protocol": "telnet",
                        "username": "old-user",
                        "password": "old-pass",
                        "port": 23,
                    }
                ],
            }
        ),
    )

    fake_response = ReturnResponse.ok(
        data={"success_count": 1, "failed_count": 0, "success": [], "failed": []}
    )
    fake_service = _FakeBackupService(captured_configs, fake_response)
    monkeypatch.setattr(
        "pytbox.cli.network.commands.NetworkBackupService",
        lambda: fake_service,
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "network",
            "backup",
            "--config",
            str(config_path),
            "--os",
            "cisco",
            "--ip",
            "10.1.1.100",
            "--protocol",
            "ssh",
            "--username",
            "new-user",
            "--password",
            "new-pass",
        ],
    )

    assert result.exit_code == 0
    merged_device = captured_configs[0]["devices"][0]
    assert merged_device["os"] == "cisco"
    assert merged_device["ip"] == "10.1.1.100"
    assert merged_device["protocol"] == "ssh"
    assert merged_device["username"] == "new-user"
    assert merged_device["password"] == "new-pass"


def test_network_backup_returns_exit_1_on_failure(
    monkeypatch: Any,
) -> None:
    """CLI should return exit code 1 when backup service fails."""
    captured_configs: List[Dict[str, Any]] = []
    fake_response = ReturnResponse.fail(
        code=1,
        msg="failed",
        data={"success_count": 0, "failed_count": 1, "success": [], "failed": []},
    )
    fake_service = _FakeBackupService(captured_configs, fake_response)
    monkeypatch.setattr(
        "pytbox.cli.network.commands.NetworkBackupService",
        lambda: fake_service,
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "network",
            "backup",
            "--os",
            "h3c",
            "--ip",
            "10.0.0.8",
            "--protocol",
            "ssh",
            "--username",
            "ops",
            "--password",
            "x",
        ],
    )

    assert result.exit_code == 1


def test_network_backup_config_plus_direct_uses_config_password_when_absent(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    """Use config password when direct mode does not provide --password."""
    captured_configs: List[Dict[str, Any]] = []
    config_path = tmp_path / "devices.yml"
    config_path.write_text("devices: []", encoding="utf-8")

    monkeypatch.setattr(
        "pytbox.cli.network.commands.load_backup_config",
        lambda _path: ReturnResponse.ok(
            data={
                "output_dir": "./backups/network",
                "timeout": 10,
                "retries": 3,
                "devices": [
                    {
                        "ip": "10.2.2.2",
                        "os": "huawei",
                        "protocol": "ssh",
                        "username": "old-user",
                        "password": "config-pass",
                    }
                ],
            }
        ),
    )

    fake_response = ReturnResponse.ok(
        data={"success_count": 1, "failed_count": 0, "success": [], "failed": []}
    )
    fake_service = _FakeBackupService(captured_configs, fake_response)
    monkeypatch.setattr(
        "pytbox.cli.network.commands.NetworkBackupService",
        lambda: fake_service,
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "network",
            "backup",
            "--config",
            str(config_path),
            "--os",
            "cisco",
            "--ip",
            "10.2.2.20",
            "--protocol",
            "ssh",
            "--username",
            "new-user",
        ],
    )

    assert result.exit_code == 0
    assert captured_configs[0]["devices"][0]["password"] == "config-pass"
