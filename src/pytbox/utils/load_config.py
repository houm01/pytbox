#!/usr/bin/env python3

import os
import json
from typing import Any, Dict, Optional

try:
    # Python 3.11+ 标准库
    import tomllib as toml  # type: ignore
    _TOML_NEEDS_BINARY_FILE = True
except ModuleNotFoundError:
    try:
        # Python <3.11 的轻量实现
        import tomli as toml  # type: ignore
        _TOML_NEEDS_BINARY_FILE = True
    except ModuleNotFoundError:
        # 第三方 toml 库（文本文件）
        import toml  # type: ignore
        _TOML_NEEDS_BINARY_FILE = False

from ..onepassword_connect import OnePasswordConnect
# from pytbox.onepassword_connect import OnePasswordConnect


def _load_jsonfile_data(jsonfile_path: Optional[str]) -> Optional[Dict[str, Any]]:
    """Load JSON file data once for ``jsonfile,`` placeholders.

    Args:
        jsonfile_path: Path to the JSON file.

    Returns:
        Optional[Dict[str, Any]]: Parsed JSON dictionary, or ``None`` when the
            file does not exist, parse fails, or JSON root is not an object.
    """
    if not jsonfile_path or not os.path.exists(jsonfile_path):
        return None

    try:
        with open(jsonfile_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None

    return data if isinstance(data, dict) else None


def _replace_values(
    data: Any,
    oc: Optional[OnePasswordConnect]=None,
    jsonfile_path: Optional[str]=None,
    jsonfile_data: Optional[Dict[str, Any]]=None,
) -> Any:
    """Recursively resolve special placeholders in config values.

    Supported placeholder prefixes:
    - ``1password,item_id,field_name``
    - ``password,item_id,field_name``
    - ``jsonfile,key`` (supports dotted key path)

    Args:
        data: Config value to resolve.
        oc: Optional OnePasswordConnect client.
        jsonfile_path: JSON file path used for ``jsonfile`` fallback.
        jsonfile_data: Preloaded JSON data for lookup reuse.

    Returns:
        Any: Resolved value.
    """
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            result[k] = _replace_values(v, oc, jsonfile_path, jsonfile_data)
        return result
    elif isinstance(data, list):
        return [_replace_values(item, oc, jsonfile_path, jsonfile_data) for item in data]
    elif isinstance(data, str):
        # 处理 1password,item_id,field_name 格式
        if data.startswith("1password,") and oc:
            parts = data.split(",")
            if len(parts) >= 3:
                item_id = parts[1]
                field_name = parts[2]
                try:
                    # 通过 item_id 获取项目，然后从字段中提取对应值
                    item = oc.get_item(item_id)
                    for field in item.fields:
                        if field.label == field_name:
                            return field.value
                except (AttributeError, KeyError, ValueError):
                    pass
                return data  # 如果找不到字段，返回原始值
        # 处理 password,item_id,field_name 格式  
        elif data.startswith("password,") and oc:
            parts = data.split(",")
            if len(parts) >= 3:
                item_id = parts[1]
                field_name = parts[2]
                try:
                    # 通过 item_id 获取项目，然后从字段中提取对应值
                    item = oc.get_item(item_id)
                    for field in item.fields:
                        if field.label == field_name:
                            return field.value
                except (AttributeError, KeyError, ValueError):
                    pass
                return data  # 如果找不到字段，返回原始值
        # 处理 jsonfile,key 格式
        elif data.startswith("jsonfile,"):
            parts = data.split(",", 1)  # 只分割一次，防止 key 中包含逗号
            if len(parts) >= 2:
                key = parts[1]

                # 尝试从预加载的 JSON 数据获取值（支持嵌套键，如 "db.password"）
                value: Any = jsonfile_data
                if isinstance(value, dict):
                    for key_part in key.split("."):
                        if isinstance(value, dict) and key_part in value:
                            value = value[key_part]
                        else:
                            value = None
                            break
                    if value is not None:
                        return value

                # 如果从 JSON 文件获取失败，尝试从环境变量获取
                env_value = os.getenv(key)
                if env_value is not None:
                    return env_value
                    
                return data  # 如果都获取不到，返回原始值
        return data
    else:
        return data


def load_config_by_file(
        path: str='/workspaces/pytbox/src/pytbox/alert/config/config.toml', 
        oc_vault_id: Optional[str]=None, 
        jsonfile: str="/data/jsonfile.json",
    ) -> Dict[str, Any]:
    """Load config from TOML/JSON and resolve supported placeholders.

    Args:
        path: Config file path.
        oc_vault_id: OnePassword vault ID. Enables 1Password lookup when set.
        jsonfile: JSON file path for ``jsonfile,`` lookups.

    Returns:
        Dict[str, Any]: Loaded and resolved config.
    """
    if path.endswith('.toml'):
        if _TOML_NEEDS_BINARY_FILE:
            # tomllib/tomli 需要以二进制模式读取
            with open(path, 'rb') as f:
                config = toml.load(f)
        else:
            # 第三方 toml 库使用文本模式
            with open(path, 'r', encoding='utf-8') as f:
                config = toml.load(f)
    else:
        # 如果不是 toml 文件，假设是其他格式，这里可以扩展
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
    # 处理配置值替换
    oc = None
    if oc_vault_id:
        oc = OnePasswordConnect(vault_id=oc_vault_id)

    # JSON 文件只加载一次，避免在递归替换时重复 IO
    jsonfile_data = _load_jsonfile_data(jsonfile)

    # 替换配置中的特殊值（1password, password, jsonfile）
    config = _replace_values(config, oc, jsonfile, jsonfile_data)

    return config
