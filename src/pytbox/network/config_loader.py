#!/usr/bin/env python3

"""Network backup config loader."""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict

from pytbox.schemas.codes import RespCode
from pytbox.schemas.response import ReturnResponse

try:
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]

try:
    import tomli  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    tomli = None  # type: ignore[assignment]

try:
    import toml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    toml = None  # type: ignore[assignment]


DEFAULT_OUTPUT_DIR = "./backups/network"
DEFAULT_TIMEOUT = 10
DEFAULT_RETRIES = 3

_LOGGER = logging.getLogger(__name__)


def _log_step(task_id: str, target: str, result: str, start_ts: float) -> None:
    """Log key steps for external IO.

    Args:
        task_id: Correlation id.
        target: Config file target.
        result: Step result.
        start_ts: Monotonic start timestamp.
    """
    duration_ms = int((time.monotonic() - start_ts) * 1000)
    _LOGGER.info(
        "task_id=%s target=%s result=%s duration_ms=%s",
        task_id,
        target,
        result,
        duration_ms,
    )


def _normalize_retries(value: Any) -> int:
    """Normalize retries into [1, 3].

    Args:
        value: Raw retries value.

    Returns:
        int: Normalized retries.
    """
    try:
        retries = int(value)
    except (TypeError, ValueError):
        retries = DEFAULT_RETRIES
    return min(max(retries, 1), 3)


def _normalize_timeout(value: Any) -> int:
    """Normalize timeout into a positive integer.

    Args:
        value: Raw timeout value.

    Returns:
        int: Normalized timeout.
    """
    try:
        timeout = int(value)
    except (TypeError, ValueError):
        timeout = DEFAULT_TIMEOUT
    return timeout if timeout > 0 else DEFAULT_TIMEOUT


def _validate_device(device: Dict[str, Any], index: int) -> ReturnResponse:
    """Validate one device config item.

    Args:
        device: Device config item.
        index: Device index in config.

    Returns:
        ReturnResponse: Validation result.
    """
    required_fields = ("ip", "os", "protocol", "username", "password")
    missing = [field for field in required_fields if not device.get(field)]
    if missing:
        return ReturnResponse.fail(
            code=RespCode.INVALID_PARAMS,
            msg=f"devices[{index}] 缺少字段: {', '.join(missing)}",
        )

    protocol = str(device.get("protocol", "")).lower()
    if protocol not in {"ssh", "telnet"}:
        return ReturnResponse.fail(
            code=RespCode.INVALID_PARAMS,
            msg=f"devices[{index}] protocol 仅支持 ssh/telnet",
        )

    return ReturnResponse.ok()


def _normalize_device(device: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize one device config item.

    Args:
        device: Raw device config item.

    Returns:
        dict[str, Any]: Normalized device config.
    """
    protocol = str(device.get("protocol", "ssh")).lower()
    default_port = 22 if protocol == "ssh" else 23
    normalized = {
        "ip": str(device["ip"]).strip(),
        "os": str(device["os"]).strip().lower(),
        "protocol": protocol,
        "username": str(device["username"]),
        "password": str(device["password"]),
        "port": int(device.get("port", default_port)),
    }
    if device.get("enable_password"):
        normalized["enable_password"] = str(device["enable_password"])
    if device.get("backup_command"):
        normalized["backup_command"] = str(device["backup_command"])
    if device.get("disable_paging_command"):
        normalized["disable_paging_command"] = str(device["disable_paging_command"])
    if device.get("device_type"):
        normalized["device_type"] = str(device["device_type"])
    return normalized


def _load_yaml(path: Path) -> ReturnResponse:
    """Load YAML config.

    Args:
        path: Config file path.

    Returns:
        ReturnResponse: Parsed config.
    """
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError:
        return ReturnResponse.fail(
            code=RespCode.INTERNAL_ERROR,
            msg="未安装 pyyaml，无法解析 YAML 配置",
        )

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            return ReturnResponse.fail(
                code=RespCode.INVALID_PARAMS,
                msg="配置文件内容必须是对象结构",
            )
        return ReturnResponse.ok(data=data)
    except OSError as exc:
        return ReturnResponse.fail(
            code=RespCode.INTERNAL_ERROR,
            msg=f"读取配置文件失败: {exc}",
        )


def _load_json(path: Path) -> ReturnResponse:
    """Load JSON config.

    Args:
        path: Config file path.

    Returns:
        ReturnResponse: Parsed config.
    """
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return ReturnResponse.fail(
                code=RespCode.INVALID_PARAMS,
                msg="配置文件内容必须是对象结构",
            )
        return ReturnResponse.ok(data=data)
    except (OSError, json.JSONDecodeError) as exc:
        return ReturnResponse.fail(
            code=RespCode.INTERNAL_ERROR,
            msg=f"读取配置文件失败: {exc}",
        )


def _load_toml(path: Path) -> ReturnResponse:
    """Load TOML config.

    Args:
        path: Config file path.

    Returns:
        ReturnResponse: Parsed config.
    """
    try:
        if tomllib is not None:
            with path.open("rb") as handle:
                data = tomllib.load(handle)
        elif tomli is not None:  # pragma: no cover
            with path.open("rb") as handle:
                data = tomli.load(handle)
        elif toml is not None:  # pragma: no cover
            with path.open("r", encoding="utf-8") as handle:
                data = toml.load(handle)
        else:
            return ReturnResponse.fail(
                code=RespCode.INTERNAL_ERROR,
                msg="未安装 TOML 解析依赖",
            )
    except OSError as exc:
        return ReturnResponse.fail(
            code=RespCode.INTERNAL_ERROR,
            msg=f"读取配置文件失败: {exc}",
        )
    except Exception as exc:  # noqa: BLE001
        return ReturnResponse.fail(
            code=RespCode.INVALID_PARAMS,
            msg=f"TOML 配置解析失败: {exc}",
        )

    if not isinstance(data, dict):
        return ReturnResponse.fail(
            code=RespCode.INVALID_PARAMS,
            msg="配置文件内容必须是对象结构",
        )
    return ReturnResponse.ok(data=data)


def load_backup_config(path: str) -> ReturnResponse:
    """Load and validate backup config from file.

    Args:
        path: Config file path. Supports yaml/yml/json/toml.

    Returns:
        ReturnResponse: Loaded and normalized config.
    """
    config_path = Path(path).expanduser()
    if not config_path.exists():
        return ReturnResponse.fail(
            code=RespCode.INVALID_PARAMS,
            msg=f"配置文件不存在: {config_path}",
        )

    task_id = uuid.uuid4().hex[:8]
    start_ts = time.monotonic()
    suffix = config_path.suffix.lower()

    if suffix in {".yaml", ".yml"}:
        loaded = _load_yaml(config_path)
    elif suffix == ".json":
        loaded = _load_json(config_path)
    elif suffix == ".toml":
        loaded = _load_toml(config_path)
    else:
        return ReturnResponse.fail(
            code=RespCode.INVALID_PARAMS,
            msg=f"不支持的配置格式: {suffix}",
        )

    if loaded.code != 0:
        _log_step(task_id, str(config_path), "fail", start_ts)
        return loaded

    raw = loaded.data if isinstance(loaded.data, dict) else {}
    devices = raw.get("devices", [])
    if devices is None:
        devices = []
    if not isinstance(devices, list):
        _log_step(task_id, str(config_path), "fail", start_ts)
        return ReturnResponse.fail(
            code=RespCode.INVALID_PARAMS,
            msg="devices 必须是列表",
        )

    normalized_devices = []
    for index, item in enumerate(devices):
        if not isinstance(item, dict):
            _log_step(task_id, str(config_path), "fail", start_ts)
            return ReturnResponse.fail(
                code=RespCode.INVALID_PARAMS,
                msg=f"devices[{index}] 必须是对象",
            )
        validation = _validate_device(item, index)
        if validation.code != 0:
            _log_step(task_id, str(config_path), "fail", start_ts)
            return validation
        normalized_devices.append(_normalize_device(item))

    normalized = {
        "output_dir": str(raw.get("output_dir") or DEFAULT_OUTPUT_DIR),
        "timeout": _normalize_timeout(raw.get("timeout")),
        "retries": _normalize_retries(raw.get("retries")),
        "devices": normalized_devices,
    }
    _log_step(task_id, str(config_path), "ok", start_ts)
    return ReturnResponse.ok(data=normalized, msg="配置加载成功")

