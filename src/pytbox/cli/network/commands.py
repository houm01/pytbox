"""Network CLI commands."""

from __future__ import annotations

from typing import Any, Dict

import click

from pytbox.network.config_loader import load_backup_config
from pytbox.network.device_backup import NetworkBackupService


def _has_direct_args(
    device_os: str | None,
    ip: str | None,
    protocol: str | None,
    username: str | None,
    password: str | None,
) -> bool:
    """Check whether direct device args are provided.

    Args:
        device_os: Device OS.
        ip: Device IP.
        protocol: Device protocol.
        username: Device username.
        password: Device password.

    Returns:
        bool: Whether any direct arg exists.
    """
    return any([device_os, ip, protocol, username, password])


def _build_merged_direct_device(
    base_config: Dict[str, Any],
    device_os: str,
    ip: str,
    protocol: str,
    username: str,
    password: str,
) -> Dict[str, Any]:
    """Build single direct-mode device and merge with config.

    Args:
        base_config: Config loaded from file or defaults.
        device_os: Device OS.
        ip: Device IP.
        protocol: Device protocol.
        username: Device username.
        password: Device password.

    Returns:
        dict[str, Any]: Merged device config.
    """
    base_device: Dict[str, Any] = {}
    devices = base_config.get("devices", [])
    if devices and isinstance(devices, list) and isinstance(devices[0], dict):
        base_device = devices[0].copy()

    overrides = {
        "os": device_os.lower(),
        "ip": ip,
        "protocol": protocol.lower(),
        "username": username,
        "password": password,
    }
    base_device.update(overrides)
    return base_device


@click.group()
def network_group() -> None:
    """Network automation commands."""


@network_group.command("backup")
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False),
    help="配置文件路径 (yaml/yml/json/toml)",
)
@click.option(
    "--os",
    "device_os",
    type=click.Choice(["cisco", "huawei", "h3c", "ruijie"], case_sensitive=False),
    help="设备厂商",
)
@click.option("--ip", "ip", type=str, help="设备 IP 地址")
@click.option(
    "--protocol",
    "protocol",
    type=click.Choice(["ssh", "telnet"], case_sensitive=False),
    help="连接协议",
)
@click.option("--username", "username", type=str, help="登录用户名")
@click.option("--password", "password", type=str, help="登录密码")
@click.option("--output-dir", "output_dir", type=str, default=None, help="备份输出目录")
def backup_command(
    config_path: str | None,
    device_os: str | None,
    ip: str | None,
    protocol: str | None,
    username: str | None,
    password: str | None,
    output_dir: str | None,
) -> None:
    """Backup device running configuration.

    Args:
        config_path: Config file path.
        device_os: Device OS.
        ip: Device IP.
        protocol: Connection protocol.
        username: Login username.
        password: Login password.
        output_dir: Optional output directory override.
    """
    direct_mode = _has_direct_args(device_os, ip, protocol, username, password)
    if not config_path and not direct_mode:
        raise click.UsageError("请提供 --config 或直连参数(--os/--ip/--protocol/--username)")

    merged_config: Dict[str, Any] = {
        "output_dir": "./backups/network",
        "timeout": 10,
        "retries": 3,
        "devices": [],
    }
    if config_path:
        loaded = load_backup_config(config_path)
        if loaded.code != 0:
            raise click.ClickException(loaded.msg)
        if not isinstance(loaded.data, dict):
            raise click.ClickException("配置格式无效")
        merged_config = loaded.data

    if direct_mode:
        required_direct_fields = {
            "os": device_os,
            "ip": ip,
            "protocol": protocol,
            "username": username,
        }
        missing_direct = [
            field_name
            for field_name, field_value in required_direct_fields.items()
            if not field_value
        ]
        if missing_direct:
            raise click.UsageError(
                f"直连模式缺少参数: {', '.join(missing_direct)}"
            )
        base_password = ""
        base_devices = merged_config.get("devices", [])
        if (
            isinstance(base_devices, list)
            and base_devices
            and isinstance(base_devices[0], dict)
        ):
            base_password = str(base_devices[0].get("password") or "")

        password_value = password or base_password
        if not password_value:
            password_value = click.prompt("Password", hide_input=True)
        merged_device = _build_merged_direct_device(
            base_config=merged_config,
            device_os=str(device_os),
            ip=str(ip),
            protocol=str(protocol),
            username=str(username),
            password=str(password_value),
        )
        merged_config["devices"] = [merged_device]
    elif not merged_config.get("devices"):
        raise click.UsageError("配置文件中 devices 不能为空")

    if output_dir:
        merged_config["output_dir"] = output_dir

    service = NetworkBackupService()
    response = service.backup_devices(merged_config)
    summary = response.data if isinstance(response.data, dict) else {}
    success_count = int(summary.get("success_count", 0))
    failed_count = int(summary.get("failed_count", 0))

    click.echo(f"Backup finished. success={success_count}, failed={failed_count}")
    if response.code != 0:
        raise SystemExit(1)
