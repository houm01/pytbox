#!/usr/bin/env python3


try:
    import toml
except ImportError:
    import tomllib as toml  # Python 3.11+ fallback
from pytbox.onepassword_connect import OnePasswordConnect


def _replace_1password_values(data, oc):
    """
    递归处理配置数据，替换 1password 和 password 开头的值
    
    Args:
        data: 配置数据（dict, list, str 等）
        oc: OnePasswordConnect 实例
    
    Returns:
        处理后的数据
    """
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            result[k] = _replace_1password_values(v, oc)
        return result
    elif isinstance(data, list):
        return [_replace_1password_values(item, oc) for item in data]
    elif isinstance(data, str):
        # 处理 1password,item_id,field_name 格式
        if data.startswith("1password,"):
            parts = data.split(",")
            if len(parts) >= 3:
                item_id = parts[1]
                field_name = parts[2]
                # 通过 item_id 获取项目，然后从字段中提取对应值
                item = oc.get_item(item_id)
                for field in item.fields:
                    if field.label == field_name:
                        return field.value
                return data  # 如果找不到字段，返回原始值
        # 处理 password,item_id,field_name 格式  
        elif data.startswith("password,"):
            parts = data.split(",")
            if len(parts) >= 3:
                item_id = parts[1]
                field_name = parts[2]
                # 通过 item_id 获取项目，然后从字段中提取对应值
                item = oc.get_item(item_id)
                for field in item.fields:
                    if field.label == field_name:
                        return field.value
                return data  # 如果找不到字段，返回原始值
        return data
    else:
        return data


def load_config_by_file(path: str='/workspaces/pytbox/src/pytbox/alert/config/config.toml', oc_vault_id: str=None) -> dict:
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
            import json
            config = json.load(f)
            
        if oc_vault_id:
            oc = OnePasswordConnect(vault_id=oc_vault_id)
            config = _replace_1password_values(config, oc)
            
        return config


if __name__ == "__main__":
    print(load_config_by_file(path='/workspaces/pytbox/tests/alert/config_dev.toml', oc_vault_id="hcls5uxuq5dmxorw6rfewefdsa"))