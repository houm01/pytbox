#!/usr/bin/env python3

from pytbox.database.victoriametrics import VictoriaMetrics
from pytbox.utils.load_config import load_config_by_file
from pytbox.alert.alert_handler import AlertHandler
from pytbox.base import MongoClient, feishu_client

config = load_config_by_file(path='/workspaces/pytbox/tests/alert/config_dev.toml')
mongo_alert = MongoClient(collection='alert_test', oc_vault_id="hcls5uxuq5dmxorw6rfewefdsa")
feishu = feishu_client(oc_vault_id="hcls5uxuq5dmxorw6rfewefdsa")
alert_handler = AlertHandler(
    config=config,
    mongo_client=mongo_alert,
    feishu_client=feishu
    )


def run():
    docs = mongo_alert.query_alert_not_resolved()
    for doc in docs:
        print(doc)


if __name__ == "__main__":
    run()