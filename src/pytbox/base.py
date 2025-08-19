#!/usr/bin/env python3


from pytbox.database.mongo import Mongo
from pytbox.utils.load_config import load_config_by_file
from pytbox.database.victoriametrics import VictoriaMetrics
from pytbox.feishu.client import Client as FeishuClient
from pytbox.dida365 import Dida365


def MongoClient(collection, config_path='/workspaces/pytbox/tests/alert/config_dev.toml', oc_vault_id=None):
    config = load_config_by_file(path=config_path, oc_vault_id=oc_vault_id)
    return Mongo(
        host=config['mongo']['host'],
        port=config['mongo']['port'],
        username=config['mongo']['username'],
        password=config['mongo']['password'],
        auto_source=config['mongo']['auto_source'],
        db_name=config['mongo']['db_name'],
        collection=collection
    )

def vm_client(config_path='/workspaces/pytbox/tests/alert/config_dev.toml', oc_vault_id=None):
    config = load_config_by_file(path=config_path, oc_vault_id=oc_vault_id)
    return VictoriaMetrics(
        url=config['victoriametrics']['url']
    )

def feishu_client(config_path='/workspaces/pytbox/tests/alert/config_dev.toml', oc_vault_id=None):
    config = load_config_by_file(path=config_path, oc_vault_id=oc_vault_id)
    return FeishuClient(
        app_id=config['feishu']['app_id'],
        app_secret=config['feishu']['app_secret']
    )

def dida_client(config_path='/workspaces/pytbox/tests/alert/config_dev.toml', oc_vault_id=None):
    config = load_config_by_file(path=config_path, oc_vault_id=oc_vault_id)
    return Dida365(
        cookie=config['dida']['cookie'],
        access_token=config['dida']['access_token']
    )