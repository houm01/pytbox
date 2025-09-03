#!/usr/bin/env python3

import json
from pytbox.utils.response import ReturnResponse


def load_dev_file(file_path: str) -> ReturnResponse:
    """从开发环境文件加载数据并返回 ReturnResponse 对象
    
    Args:
        file_path: JSON 文件路径
        
    Returns:
        ReturnResponse: 包装后的响应对象
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 如果已经是 ReturnResponse 格式的字典，直接转换
        if isinstance(data, dict) and 'code' in data and 'msg' in data:
            return ReturnResponse(
                code=data.get('code', 0),
                msg=data.get('msg', ''),
                data=data.get('data', None)
            )
        else:
            # 如果是其他格式，包装成成功响应
            return ReturnResponse(
                code=0,
                msg='开发文件加载成功',
                data=data
            )
    except FileNotFoundError:
        return ReturnResponse(
            code=4,
            msg=f'开发文件未找到: {file_path}',
            data=None
        )
    except json.JSONDecodeError as e:
        return ReturnResponse(
            code=1,
            msg=f'JSON 解析错误: {str(e)}',
            data=None
        )