#!/usr/bin/env python3
"""
开发环境可执行文件 - 支持新的模块化 CLI
"""

import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
src_path = Path(__file__).parent / 'src'
if src_path.exists():
    sys.path.insert(0, str(src_path))

from pytbox.cli import main

if __name__ == "__main__":
    main()
