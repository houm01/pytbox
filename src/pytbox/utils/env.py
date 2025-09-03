#!/usr/bin/env python3

import os
from typing import Literal


def get_env_by_file_exist(file_path: str) -> Literal['prod', 'dev']:
    '''
    检查当前的运行环境

    Returns:
        Literal['prod', 'dev']: 环境
    '''
    if os.path.exists(file_path):
        return 'prod'
    else:
        return 'dev'


def get_env_by_os_environment(check_key: str='ENV') -> Literal['dev', 'prod']:
    '''
    根据环境变量获取环境

    Returns:
        Literal['dev', 'prod']: 环境，dev 表示开发环境，prod 表示生产环境
    '''
    if os.getenv(check_key) == 'dev':
        return 'dev'
    else:
        return 'prod'