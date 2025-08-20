#!/usr/bin/env python3

from pytbox.database.victoriametrics import VictoriaMetrics
from pytbox.utils.load_config import load_config_by_file
from pytbox.alert.alert_handler import AlertHandler
from pytbox.base import MongoClient, feishu_client, dida_client

config = load_config_by_file(path='/workspaces/pytbox/tests/alert/config_dev.toml')
mongo_alert = MongoClient(collection='alert_test', oc_vault_id="hcls5uxuq5dmxorw6rfewefdsa")
feishu = feishu_client(oc_vault_id="hcls5uxuq5dmxorw6rfewefdsa")
dida = dida_client(oc_vault_id="hcls5uxuq5dmxorw6rfewefdsa")

alert_handler = AlertHandler(
    config=config,
    mongo_client=mongo_alert,
    feishu_client=feishu,
    dida_client=dida
)

vm = VictoriaMetrics(url=config['victoriametrics']['url'])



def ping(target):
    
    r = vm.check_ping_result(target=target, last_minute=config['alert']['ping']['last_minute'])
    if r.code == 1:
        print(r)
        alert_handler.send_alert(
            event_type='trigger',
            event_name=config['alert']['ping']['event_name'],
            event_content=f"{target} {config['alert']['ping']['event_name']}",
            entity_name=target,
            priority=config['alert']['ping']['priority'],
            resolved_expr={
                "target": target
            }
        )

def resolved():
    docs = mongo_alert.query_alert_not_resolved(event_name=config['alert']['ping']['event_name'])
    for doc in docs:
        print(doc)
        r = vm.check_ping_result(target=doc['resolved_expr']['target'], last_minute=config['alert']['ping']['last_minute'])
        print(r)
        if r.code == 2:
            alert_handler.send_alert(
                event_type='resolved',
                event_name=config['alert']['ping']['event_name'],
                event_content=f"{doc['resolved_expr']['target']} {config['alert']['ping']['event_name']}",
                entity_name=doc['entity_name'],
                priority=doc['priority'],
                mongo_id=doc['_id']
            )


if __name__ == "__main__":
    # config = load_config()
    ping("121.46.237.185")
    # resolved()