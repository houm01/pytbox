"""
Categraf 相关命令 - 支持 rich 美化输出
"""

import shutil
from pathlib import Path
import click
from ...utils.richutils import RichUtils
from ...categraf.build_config import BuildConfig



rich_utils = RichUtils()


@click.group()
def categraf_group():
    """Categraf 配置管理工具"""
    pass


@categraf_group.command('get-instances')
@click.option('--output-dir', '-o', type=click.Path(exists=True), default='.')
def get_instances(output_dir):
    """获取 Categraf 实例配置"""
    instances_template_path = Path(__file__).parent.parent.parent / 'categraf' / 'instances.toml'
    dest_path = Path(output_dir) / 'instances.toml'
    shutil.copy(instances_template_path, dest_path)
    rich_utils.print(msg=f'已将 {instances_template_path} 复制到 {dest_path}', style='info')


@categraf_group.command('build-config')
@click.option('--instances', '-i', type=click.Path(exists=True), default='.')
@click.option('--output-dir', '-o', type=click.Path(exists=True), default='.')
def build_config(instances, output_dir):
    '''
    生成配置

    Args:
        instances (_type_): _description_
        output_dir (_type_): _description_
    '''
    # ping_template_path = Path(__file__).parent.parent.parent / 'categraf' / 'ping.toml'
    # dest_path = Path(output_dir) / 'ping.toml'
    # shutil.copy(ping_template_path, dest_path)
    # rich_utils.print(msg=f'已将 {ping_template_path} 复制到 {dest_path}', style='info')
    # 获取 instances 和 output_dir 的绝对路径
    instances_abs = str(Path(instances).resolve())
    output_dir_abs = str(Path(output_dir).resolve())
    
    rich_utils.print(msg=f'instances 绝对路径: {instances_abs}', style='info')
    rich_utils.print(msg=f'output_dir 绝对路径: {output_dir_abs}', style='info')

    build_config = BuildConfig(instances_abs, output_dir_abs)
    build_config.run()