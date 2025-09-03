#!/usr/bin/env python3

import click
from pytbox.database.victoriametrics import VictoriaMetrics
from pytbox.utils.richutils import RichUtils

rich_utils = RichUtils()

@click.group()
def vm_group():
    """VictoriaMetrics 查询工具"""
    pass


@vm_group.command('query')
@click.option('--url', '-u', type=str, required=True)
@click.option('--query', '-q', type=str, required=True)
def query(url, query):
    """查询 VM 数据"""
    vm_client = VictoriaMetrics(url=url)
    r = vm_client.query(query, output_format='json')
    rich_utils.print(msg=r)
