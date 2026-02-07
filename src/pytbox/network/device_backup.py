#!/usr/bin/env python3

"""Network device backup service."""

from __future__ import annotations

import logging
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from pytbox.schemas.codes import RespCode
from pytbox.schemas.response import ReturnResponse

try:
    from netmiko import ConnectHandler  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    ConnectHandler = None  # type: ignore[assignment]


DEVICE_TYPE_MAP = {
    "cisco": {"ssh": "cisco_ios", "telnet": "cisco_ios_telnet"},
    "huawei": {"ssh": "huawei", "telnet": "huawei_telnet"},
    "h3c": {"ssh": "hp_comware", "telnet": "hp_comware_telnet"},
    "ruijie": {"ssh": "ruijie_os", "telnet": "ruijie_os_telnet"},
}

BACKUP_COMMAND_MAP = {
    "cisco": "show running-config",
    "huawei": "display current-configuration",
    "h3c": "display current-configuration",
    "ruijie": "show running-config",
}

DISABLE_PAGING_COMMAND_MAP = {
    "cisco": "terminal length 0",
    "huawei": "screen-length 0 temporary",
    "h3c": "screen-length disable",
    "ruijie": "terminal length 0",
}


class NetworkBackupService:
    """Backup service for network devices."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """Initialize backup service.

        Args:
            logger: Optional custom logger.
        """
        self.logger = logger or logging.getLogger(__name__)

    def backup_devices(self, config: Dict[str, Any]) -> ReturnResponse:
        """Backup devices defined in config.

        Args:
            config: Backup runtime config.

        Returns:
            ReturnResponse: Backup summary response.
        """
        if ConnectHandler is None:
            return ReturnResponse.fail(
                code=RespCode.INTERNAL_ERROR,
                msg="未安装 netmiko，请先安装后再执行网络设备备份",
            )

        devices = config.get("devices", [])
        if not isinstance(devices, list) or not devices:
            return ReturnResponse.fail(
                code=RespCode.INVALID_PARAMS,
                msg="devices 不能为空",
            )

        output_dir = str(config.get("output_dir") or "./backups/network")
        timeout = self._normalize_timeout(config.get("timeout", 10))
        retries = self._normalize_retries(config.get("retries", 3))

        summary: Dict[str, Any] = {
            "success_count": 0,
            "failed_count": 0,
            "success": [],
            "failed": [],
        }
        for index, device in enumerate(devices):
            if not isinstance(device, dict):
                summary["failed_count"] += 1
                summary["failed"].append(
                    {"index": index, "reason": "设备配置必须是对象类型"}
                )
                continue

            response = self._backup_single_device(
                device=device,
                output_dir=output_dir,
                timeout=timeout,
                retries=retries,
            )
            if response.code == 0:
                summary["success_count"] += 1
                summary["success"].append(response.data)
            else:
                summary["failed_count"] += 1
                failed_item = {
                    "ip": str(device.get("ip", "")),
                    "os": str(device.get("os", "")),
                    "reason": response.msg,
                }
                summary["failed"].append(failed_item)

        if summary["failed_count"] > 0:
            return ReturnResponse.fail(
                code=RespCode.INTERNAL_ERROR,
                msg="部分设备备份失败",
                data=summary,
            )
        return ReturnResponse.ok(data=summary, msg="设备配置备份完成")

    def _normalize_timeout(self, timeout: Any) -> int:
        """Normalize timeout.

        Args:
            timeout: Timeout value.

        Returns:
            int: Normalized timeout.
        """
        try:
            timeout_value = int(timeout)
        except (TypeError, ValueError):
            timeout_value = 10
        return timeout_value if timeout_value > 0 else 10

    def _normalize_retries(self, retries: Any) -> int:
        """Normalize retries.

        Args:
            retries: Retries value.

        Returns:
            int: Normalized retries in range [1, 3].
        """
        try:
            retries_value = int(retries)
        except (TypeError, ValueError):
            retries_value = 3
        return min(max(retries_value, 1), 3)

    def _backup_single_device(
        self,
        device: Dict[str, Any],
        output_dir: str,
        timeout: int,
        retries: int,
    ) -> ReturnResponse:
        """Backup one device with retry.

        Args:
            device: Device config.
            output_dir: Backup output directory.
            timeout: Network timeout.
            retries: Maximum retries.

        Returns:
            ReturnResponse: Backup result.
        """
        normalized = self._normalize_device(device)
        if normalized.code != 0:
            return normalized

        normalized_device = normalized.data
        if not isinstance(normalized_device, dict):
            return ReturnResponse.fail(
                code=RespCode.INTERNAL_ERROR,
                msg="设备参数归一化失败",
            )

        last_response: ReturnResponse | None = None
        target = str(normalized_device.get("ip", "unknown"))
        task_id = uuid.uuid4().hex[:8]

        for attempt in range(1, retries + 1):
            attempt_start = time.monotonic()
            result = self._backup_single_attempt(
                device=normalized_device,
                output_dir=output_dir,
                timeout=timeout,
            )
            if result.code == 0:
                self._log_step(task_id, target, "ok", attempt_start)
                return result

            last_response = result
            if attempt < retries:
                self._log_step(task_id, target, "retry", attempt_start)
                time.sleep(2 ** (attempt - 1))
            else:
                self._log_step(task_id, target, "fail", attempt_start)

        return last_response or ReturnResponse.fail(
            code=RespCode.INTERNAL_ERROR,
            msg="设备备份失败",
        )

    def _normalize_device(self, device: Dict[str, Any]) -> ReturnResponse:
        """Normalize and validate device settings.

        Args:
            device: Device config.

        Returns:
            ReturnResponse: Normalized device payload.
        """
        required_fields = ("ip", "os", "protocol", "username", "password")
        missing = [field for field in required_fields if not device.get(field)]
        if missing:
            return ReturnResponse.fail(
                code=RespCode.INVALID_PARAMS,
                msg=f"设备配置缺少字段: {', '.join(missing)}",
            )

        os_name = str(device.get("os", "")).strip().lower()
        protocol = str(device.get("protocol", "")).strip().lower()
        if protocol not in {"ssh", "telnet"}:
            return ReturnResponse.fail(
                code=RespCode.INVALID_PARAMS,
                msg="protocol 仅支持 ssh/telnet",
            )

        explicit_device_type = device.get("device_type")
        if explicit_device_type:
            device_type = str(explicit_device_type)
        else:
            mapping = DEVICE_TYPE_MAP.get(os_name)
            if mapping is None:
                return ReturnResponse.fail(
                    code=RespCode.INVALID_PARAMS,
                    msg=f"不支持的 os: {os_name}",
                )
            device_type = mapping[protocol]

        port = device.get("port", 22 if protocol == "ssh" else 23)
        try:
            port_value = int(port)
        except (TypeError, ValueError):
            return ReturnResponse.fail(
                code=RespCode.INVALID_PARAMS,
                msg=f"端口格式错误: {port}",
            )

        normalized = {
            "ip": str(device["ip"]).strip(),
            "os": os_name,
            "protocol": protocol,
            "username": str(device["username"]),
            "password": str(device["password"]),
            "port": port_value,
            "device_type": device_type,
            "backup_command": str(
                device.get("backup_command") or BACKUP_COMMAND_MAP.get(os_name, "")
            ),
            "disable_paging_command": str(
                device.get("disable_paging_command")
                or DISABLE_PAGING_COMMAND_MAP.get(os_name, "")
            ),
        }
        if device.get("enable_password"):
            normalized["enable_password"] = str(device["enable_password"])
        return ReturnResponse.ok(data=normalized)

    def _backup_single_attempt(
        self,
        device: Dict[str, Any],
        output_dir: str,
        timeout: int,
    ) -> ReturnResponse:
        """Execute one backup attempt for a single device.

        Args:
            device: Normalized device config.
            output_dir: Backup output directory.
            timeout: Network timeout.

        Returns:
            ReturnResponse: Attempt result.
        """
        connection_kwargs = {
            "device_type": device["device_type"],
            "host": device["ip"],
            "username": device["username"],
            "password": device["password"],
            "port": device["port"],
            "conn_timeout": timeout,
            "banner_timeout": timeout,
            "auth_timeout": timeout,
            "timeout": timeout,
        }
        if device.get("enable_password"):
            connection_kwargs["secret"] = device["enable_password"]

        try:
            with ConnectHandler(**connection_kwargs) as connection:
                if device.get("enable_password"):
                    connection.enable()

                disable_paging_command = device.get("disable_paging_command", "")
                if disable_paging_command:
                    connection.send_command(
                        disable_paging_command,
                        read_timeout=timeout,
                    )

                backup_command = device.get("backup_command", "")
                if not backup_command:
                    return ReturnResponse.fail(
                        code=RespCode.INVALID_PARAMS,
                        msg=f"设备 {device['ip']} 缺少备份命令",
                    )

                content = connection.send_command(
                    backup_command,
                    read_timeout=timeout,
                )
        except Exception as exc:  # noqa: BLE001
            return ReturnResponse.fail(
                code=RespCode.INTERNAL_ERROR,
                msg=f"设备 {device['ip']} 连接或命令执行失败: {exc}",
            )

        write_result = self._write_backup_file(
            output_dir=output_dir,
            ip=str(device["ip"]),
            os_name=str(device["os"]),
            content=content,
        )
        if write_result.code != 0:
            return write_result
        payload = {
            "ip": device["ip"],
            "os": device["os"],
            "protocol": device["protocol"],
            "file_path": write_result.data.get("file_path") if write_result.data else None,
        }
        return ReturnResponse.ok(data=payload, msg=f"设备 {device['ip']} 备份成功")

    def _write_backup_file(
        self,
        output_dir: str,
        ip: str,
        os_name: str,
        content: str,
    ) -> ReturnResponse:
        """Write backup file atomically and idempotently.

        Args:
            output_dir: Root output directory.
            ip: Device IP.
            os_name: Device OS.
            content: Backup content.

        Returns:
            ReturnResponse: Write result.
        """
        current_day = datetime.now().strftime("%Y-%m-%d")
        safe_ip = re.sub(r"[^0-9A-Za-z_.-]", "_", ip)
        safe_os = re.sub(r"[^0-9A-Za-z_.-]", "_", os_name.lower())
        target_dir = Path(output_dir) / current_day
        target_path = target_dir / f"{safe_ip}_{safe_os}.cfg"
        tmp_path = target_dir / f"{safe_ip}_{safe_os}.cfg.tmp"

        for attempt in range(1, 4):
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                tmp_path.write_text(content, encoding="utf-8")
                os.replace(tmp_path, target_path)
                return ReturnResponse.ok(data={"file_path": str(target_path)})
            except OSError as exc:
                if attempt < 3:
                    time.sleep(2 ** (attempt - 1))
                    continue
                return ReturnResponse.fail(
                    code=RespCode.INTERNAL_ERROR,
                    msg=f"写入备份文件失败: {exc}",
                )
        return ReturnResponse.fail(
            code=RespCode.INTERNAL_ERROR,
            msg="写入备份文件失败",
        )

    def _log_step(self, task_id: str, target: str, result: str, start_ts: float) -> None:
        """Log key-step metrics.

        Args:
            task_id: Correlation id.
            target: Backup target.
            result: Execution result.
            start_ts: Start timestamp.
        """
        duration_ms = int((time.monotonic() - start_ts) * 1000)
        self.logger.info(
            "task_id=%s target=%s result=%s duration_ms=%s",
            task_id,
            target,
            result,
            duration_ms,
        )

