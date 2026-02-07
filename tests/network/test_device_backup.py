#!/usr/bin/env python3

"""Tests for network device backup service."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

from pytbox.network.device_backup import NetworkBackupService


def _build_fake_connect_handler(
    failures_before_success: Dict[str, int],
    captured_attempts: Dict[str, int],
) -> Any:
    """Create a fake netmiko ConnectHandler.

    Args:
        failures_before_success: Fail threshold by host.
        captured_attempts: Attempt counter by host.

    Returns:
        Any: Fake ConnectHandler class.
    """

    class _FakeConnection:
        """Fake connection object."""

        def __init__(self, **kwargs: Any) -> None:
            """Initialize fake connection.

            Args:
                **kwargs: Connection kwargs.
            """
            self.host = str(kwargs.get("host"))
            captured_attempts[self.host] = captured_attempts.get(self.host, 0) + 1
            if captured_attempts[self.host] <= failures_before_success.get(self.host, 0):
                raise RuntimeError(f"connect failure: {self.host}")
            self.secret = kwargs.get("secret")

        def __enter__(self) -> "_FakeConnection":
            """Enter context manager.

            Returns:
                _FakeConnection: Self.
            """
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            """Exit context manager.

            Args:
                exc_type: Exception type.
                exc: Exception instance.
                tb: Traceback.
            """
            _ = exc_type, exc, tb

        def enable(self) -> None:
            """Simulate enable mode."""

        def send_command(self, command: str, read_timeout: int) -> str:
            """Simulate send_command.

            Args:
                command: CLI command.
                read_timeout: Read timeout.

            Returns:
                str: Command output.
            """
            _ = read_timeout
            if "running-config" in command or "current-configuration" in command:
                return f"backup-content-{self.host}"
            return ""

    return _FakeConnection


def test_backup_devices_success_creates_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Backup success should create config file."""
    attempts: Dict[str, int] = {}
    fake_connect_handler = _build_fake_connect_handler({}, attempts)
    monkeypatch.setattr("pytbox.network.device_backup.ConnectHandler", fake_connect_handler)

    service = NetworkBackupService()
    config = {
        "output_dir": str(tmp_path),
        "timeout": 10,
        "retries": 3,
        "devices": [
            {
                "ip": "10.0.0.1",
                "os": "cisco",
                "protocol": "ssh",
                "username": "admin",
                "password": "secret",
            }
        ],
    }

    response = service.backup_devices(config)

    assert response.code == 0
    assert response.data["success_count"] == 1
    file_path = Path(response.data["success"][0]["file_path"])
    assert file_path.exists()
    assert "backup-content-10.0.0.1" in file_path.read_text(encoding="utf-8")


def test_backup_devices_continue_on_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Service should continue other devices when one fails."""
    attempts: Dict[str, int] = {}
    fake_connect_handler = _build_fake_connect_handler({"10.0.0.1": 5}, attempts)
    monkeypatch.setattr("pytbox.network.device_backup.ConnectHandler", fake_connect_handler)
    monkeypatch.setattr("pytbox.network.device_backup.time.sleep", lambda _s: None)

    service = NetworkBackupService()
    config = {
        "output_dir": str(tmp_path),
        "timeout": 10,
        "retries": 1,
        "devices": [
            {
                "ip": "10.0.0.1",
                "os": "cisco",
                "protocol": "ssh",
                "username": "admin",
                "password": "secret-a",
            },
            {
                "ip": "10.0.0.2",
                "os": "huawei",
                "protocol": "ssh",
                "username": "ops",
                "password": "secret-b",
            },
        ],
    }

    response = service.backup_devices(config)

    assert response.code != 0
    assert response.data["success_count"] == 1
    assert response.data["failed_count"] == 1


def test_backup_devices_retry_up_to_three(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Service should retry and succeed at third attempt."""
    attempts: Dict[str, int] = {}
    fake_connect_handler = _build_fake_connect_handler({"10.0.0.9": 2}, attempts)
    monkeypatch.setattr("pytbox.network.device_backup.ConnectHandler", fake_connect_handler)
    monkeypatch.setattr("pytbox.network.device_backup.time.sleep", lambda _s: None)

    service = NetworkBackupService()
    config = {
        "output_dir": str(tmp_path),
        "timeout": 10,
        "retries": 3,
        "devices": [
            {
                "ip": "10.0.0.9",
                "os": "ruijie",
                "protocol": "ssh",
                "username": "admin",
                "password": "secret",
            }
        ],
    }

    response = service.backup_devices(config)

    assert response.code == 0
    assert attempts["10.0.0.9"] == 3


def test_backup_logs_do_not_include_password(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Logs should not include password content."""
    attempts: Dict[str, int] = {}
    fake_connect_handler = _build_fake_connect_handler({"10.0.0.3": 5}, attempts)
    monkeypatch.setattr("pytbox.network.device_backup.ConnectHandler", fake_connect_handler)
    monkeypatch.setattr("pytbox.network.device_backup.time.sleep", lambda _s: None)

    service = NetworkBackupService()
    caplog.set_level("INFO")
    password_value = "super-secret-password"
    config = {
        "output_dir": str(tmp_path),
        "timeout": 10,
        "retries": 1,
        "devices": [
            {
                "ip": "10.0.0.3",
                "os": "h3c",
                "protocol": "ssh",
                "username": "ops",
                "password": password_value,
            }
        ],
    }

    _ = service.backup_devices(config)

    assert password_value not in caplog.text

