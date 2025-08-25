#!/usr/bin/env python3


from pytbox.base import meraki, get_logger, config


log = get_logger('tests.network.test_meraki')


network_name = config['meraki']['pytest']['network_name']

def test_get_networks():
    r = meraki.get_networks(tags=['PROD'])
    assert r.code == 0

def test_get_network_id_by_name():
    log.info(f"测试获取网络名称: {network_name}")
    r = meraki.get_network_id_by_name(network_name)
    log.info(f"获取到的网络 ID: {r}")
    assert r is not None

def test_get_device():
    network_id = meraki.get_network_id_by_name(network_name)
    r = meraki.get_devices(network_ids=network_id)
    log.info(r.msg)
    assert r.code == 0
    
def test_get_device_detail():
    r = meraki.get_device_detail(serial=config['meraki']['pytest']['serial'])
    log.info(r.msg)
    assert r.code == 0

def test_get_device_availabilities():
    r = meraki.get_device_availabilities(serial=config['meraki']['pytest']['serial'])
    log.info(r.data)
    assert r.code == 0

if __name__ == '__main__':
    test_get_networks()