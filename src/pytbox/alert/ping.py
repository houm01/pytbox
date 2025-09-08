#!/usr/bin/env python3

from ..database.victoriametrics import VictoriaMetrics
from ..lib.load_config import load_config


def ping(config, target):
    vm = VictoriaMetrics(url=config['victoriametrics']['url'])
    ping_status = vm.query_ping_status(target=target, last_minutes=config['alert']['ping']['last_minutes'])
    if ping_status == '不通':
        insert_alert(
            event_name=config['alert']['ping']['event_name'],
            event_content=f"{target} {config['alert']['ping']['event_name']}",
            entity_name=target,
            priority=config['alert']['ping']['priority'],
            resolved_query={
                "target": target
            }
        )


if __name__ == "__main__":
    config = load_config()
    ping(config, "10.30.35.38")