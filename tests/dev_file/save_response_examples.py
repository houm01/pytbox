#!/usr/bin/env python3
"""
演示如何正确保存 ReturnResponse 对象的不同方式
"""

import json
import pickle
from dataclasses import asdict
from pathlib import Path
from pytbox.utils.response import ReturnResponse


def create_sample_response():
    """创建一个示例 ReturnResponse 对象"""
    return ReturnResponse(
        code=0,
        msg="[ping_result_code{target='121.46.237.185'}[3m]] 查询成功!",
        data=[{
            'metric': {
                '__name__': 'ping_result_code',
                'env': 'prod',
                'type': 'public_ip',
                'name': 'Z3-备',
                'agent_hostname': 'shylf-prod-influxdb-01',
                'customer': '佳化化学',
                'isp': '电信',
                'source': 'shanghai',
                'status': 'Active',
                'target': '121.46.237.185'
            },
            'values': [
                [1756442430.932, '1'],
                [1756442445.942, '1'],
                [1756442460.907, '1'],
                [1756442475.909, '1'],
                [1756442490.887, '1'],
                [1756442505.898, '1'],
                [1756442520.908, '1'],
                [1756442535.973, '1'],
                [1756442550.889, '1'],
                [1756442565.911, '1'],
                [1756442580.885, '1'],
                [1756442595.896, '1']
            ]
        }]
    )


def save_as_json(response: ReturnResponse, filepath: str):
    """方法1: 保存为 JSON 格式（推荐用于数据交换）"""
    # 将 dataclass 转换为字典
    response_dict = asdict(response)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(response_dict, f, ensure_ascii=False, indent=2)
    
    print(f"✅ JSON 格式已保存到: {filepath}")


def save_as_pickle(response: ReturnResponse, filepath: str):
    """方法2: 保存为 Pickle 格式（用于 Python 对象序列化）"""
    with open(filepath, 'wb') as f:
        pickle.dump(response, f)
    
    print(f"✅ Pickle 格式已保存到: {filepath}")


def save_as_repr_text(response: ReturnResponse, filepath: str):
    """方法3: 保存为可读的 Python 对象字符串表示"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(repr(response))
    
    print(f"✅ Python 对象表示已保存到: {filepath}")


def load_from_json(filepath: str) -> ReturnResponse:
    """从 JSON 文件加载 ReturnResponse 对象"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return ReturnResponse(**data)


def load_from_pickle(filepath: str) -> ReturnResponse:
    """从 Pickle 文件加载 ReturnResponse 对象"""
    with open(filepath, 'rb') as f:
        return pickle.load(f)


def main():
    """主函数：演示所有保存和加载方式"""
    # 创建示例响应对象
    response = create_sample_response()
    
    # 确保输出目录存在
    output_dir = Path('/workspaces/pytbox/tests/dev_file')
    output_dir.mkdir(exist_ok=True)
    
    print("📦 原始 ReturnResponse 对象:")
    print(f"Code: {response.code}")
    print(f"Message: {response.msg}")
    print(f"Data type: {type(response.data)}")
    print(f"Data length: {len(response.data) if response.data else 0}")
    print("\n" + "="*50 + "\n")
    
    # 方法1: 保存为 JSON
    json_file = output_dir / "response.json"
    save_as_json(response, str(json_file))
    
    # 方法2: 保存为 Pickle
    pickle_file = output_dir / "response.pkl"
    save_as_pickle(response, str(pickle_file))
    
    # 方法3: 保存为文本
    text_file = output_dir / "response.txt"
    save_as_repr_text(response, str(text_file))
    
    print("\n" + "="*50 + "\n")
    
    # 验证加载
    print("🔄 验证加载功能:")
    
    # 从 JSON 加载
    loaded_from_json = load_from_json(str(json_file))
    print(f"✅ 从 JSON 加载成功: {loaded_from_json.is_success()}")
    
    # 从 Pickle 加载
    loaded_from_pickle = load_from_pickle(str(pickle_file))
    print(f"✅ 从 Pickle 加载成功: {loaded_from_pickle.is_success()}")
    
    # 比较数据
    print(f"✅ JSON 和 Pickle 数据一致: {loaded_from_json.data == loaded_from_pickle.data}")


if __name__ == "__main__":
    main()



