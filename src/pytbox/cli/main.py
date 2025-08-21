#!/usr/bin/env python3
"""
Pytbox 主命令行入口
"""

import click
from .categraf import categraf_group


@click.group()
@click.version_option()
def main():
    """Pytbox 命令行工具集合"""
    pass


# 注册子命令组
main.add_command(categraf_group, name='categraf')


if __name__ == "__main__":
    main()
