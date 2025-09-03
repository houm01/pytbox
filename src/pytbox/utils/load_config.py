#!/usr/bin/env python3

import os
import json

try:
    import toml
except ImportError:
    import tomllib as toml  # Python 3.11+ fallback
from pytbox.onepassword_connect import OnePasswordConnect


def _replace_values(data, oc=None, jsonfile_path=None):
    """
    递归处理配置数据，替换 1password、password 和 jsonfile 开头的值
    
    Args:
        data: 配置数据（dict, list, str 等）
        oc: OnePasswordConnect 实例
        jsonfile_path: JSON 文件路径
    
    Returns:
        处理后的数据
    """
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            result[k] = _replace_values(v, oc, jsonfile_path)
        return result
    elif isinstance(data, list):
        return [_replace_values(item, oc, jsonfile_path) for item in data]
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
                
                # 尝试从 JSON 文件获取值
                if jsonfile_path and os.path.exists(jsonfile_path):
                    try:
                        with open(jsonfile_path, 'r', encoding='utf-8') as f:
                            json_data = json.load(f)
                            # 支持嵌套键，如 "db.password"
                            value = json_data
                            for k in key.split('.'):
                                if isinstance(value, dict) and k in value:
                                    value = value[k]
                                else:
                                    value = None
                                    break
                            if value is not None:
                                return value
                    except (json.JSONDecodeError, FileNotFoundError, KeyError):
                        pass
                
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
        oc_vault_id: str=None, 
        jsonfile: str="/data/jsonfile.json",
    ) -> dict:
    '''
    从文件加载配置，支持 1password 集成
    
    Args:
        path (str, optional): 配置文件路径. Defaults to '/workspaces/pytbox/src/pytbox/alert/config/config.toml'.
        oc_vault_id (str, optional): OnePassword vault ID，如果提供则启用 1password 集成
        
    Returns:
        dict: 配置字典
    '''
    with open(path, 'r', encoding='utf-8') as f:
        if path.endswith('.toml'): 
            config = toml.load(f)
        else:
            # 如果不是 toml 文件，假设是其他格式，这里可以扩展
            config = json.load(f)
            
        # 处理配置值替换
        oc = None
        if oc_vault_id:
            oc = OnePasswordConnect(vault_id=oc_vault_id)
        
        # 替换配置中的特殊值（1password, password, jsonfile）
        config = _replace_values(config, oc, jsonfile)
        
        return config


if __name__ == "__main__":
    print(load_config_by_file(path='/workspaces/pytbox/tests/alert/config_dev.toml', oc_vault_id="hcls5uxuq5dmxorw6rfewefdsa"))