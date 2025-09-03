#!/usr/bin/env python3

import pytest
from pytbox.base import get_mongo, config, alert_handler, vm, env


mongo_alert = get_mongo('alert_test')

@pytest.mark.parametrize("target", ["121.46.237.185", "8.8.8.8"])
def test_ping(target):
    env = 'dev'
    r = vm.check_ping_result(target=target, last_minute=config['alert']['trigger']['ping']['last_minute'], env=env, dev_file='/workspaces/pytbox/tests/dev_file/1.json')
    if r.code == 1:
        alert_handler.send_alert(
            event_type='trigger',
            event_name=config['alert']['trigger']['ping']['event_name'],
            event_content=f"{target} {config['alert']['trigger']['ping']['event_name']}",
            entity_name=target,
            priority=config['alert']['trigger']['ping']['priority'],
            resolved_expr={
                "target": target
            }
        )

def resolved():
    docs = mongo_alert.query_alert_not_resolved(event_name=config['alert']['trigger']['ping']['event_name'])
    for doc in docs:
        print(doc)
        r = vm.check_ping_result(target=doc['resolved_expr']['target'], last_minute=config['alert']['trigger']['ping']['last_minute'])
        print(r)
        if r.code == 2:
            alert_handler.send_alert(
                event_type='resolved',
                event_name=config['alert']['trigger']['ping']['event_name'],
                event_content=f"{doc['resolved_expr']['target']} {config['alert']['trigger']['ping']['event_name']}",
                entity_name=doc['entity_name'],
                priority=doc['priority'],
                mongo_id=doc['_id']
            )


if __name__ == "__main__":
    test_ping("121.46.237.185")
    
    # resolved()