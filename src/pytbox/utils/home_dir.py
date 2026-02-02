import os

def get_home_dir():
    """
    获取home dir。

    Returns:
        Any: 返回值。
    """
    return os.environ.get('PYTHONPATH')

HOME_DIR = get_home_dir
