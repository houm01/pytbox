#!/usr/bin/env python3

from pytbox.database.victoriametrics import VictoriaMetrics
from pytbox.utils.load_config import load_config_by_file
from pytbox.alert.alert_handler import AlertHandler
from pytbox.base import MongoClient, feishu_client, dida_client

config = load_config_by_file(path='/workspaces/pytbox/tests/alert/config_dev.toml')
mongo_alert = MongoClient(collection='alert_test', oc_vault_id="hcls5uxuq5dmxorw6rfewefdsa")
feishu = feishu_client(oc_vault_id="hcls5uxuq5dmxorw6rfewefdsa")
dida = dida_client(oc_vault_id="hcls5uxuq5dmxorw6rfewefdsa")

# 创建 VictoriaMetrics 实例
vm = VictoriaMetrics(url=config['victoriametrics']['url'])