"""
通用的 Click 选项定义
"""

import click

# 通用选项
output_option = click.option(
    '--output', '-o', 
    type=click.Path(), 
    help='输出到文件'
)

format_option = click.option(
    '--format', 'output_format',
    type=click.Choice(['toml', 'json', 'yaml']),
    default='toml',
    help='输出格式'
)

data_option = click.option(
    '--data', '-d',
    help='JSON 格式的模板变量'
)

data_file_option = click.option(
    '--data-file',
    type=click.Path(exists=True),
    help='包含模板变量的 JSON 文件'
)

verbose_option = click.option(
    '--verbose', '-v',
    is_flag=True,
    help='显示详细信息'
)

quiet_option = click.option(
    '--quiet', '-q',
    is_flag=True,
    help='静默模式，只显示错误'
)
