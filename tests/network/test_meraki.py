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

def test_reboot_device():
    r = meraki.reboot_device(serial=config['meraki']['pytest']['serial'])
    print(r)
    # assert r.code == 0

def test_get_alert():
    r = meraki.get_alerts()
    # print(r)

def test_get_network_events():
    r = meraki.get_network_events(network_id=config['meraki']['pytest']['network_id'])
    for event in r.data['events']:
        if 'auth' in event['type']:
            print(event)
        # print(event['type'], event['description'])
        # print(event['description'])

def test_get_wireless_failcounter():
    r = meraki.get_devices(network_ids=config['meraki']['pytest']['network_id'])
    for i in r.data:
        if i['productType'] == 'wireless':
            print(i['serial'])
            r = meraki.get_wireless_failcounter(network_id=config['meraki']['pytest']['network_id'], timespan=60*60, serial=i['serial'])
            if len(r.data) > 2:
            
                r = meraki.reboot_device(serial=i['serial'])
                print(r)
        # print(i)
        # r = meraki.get_wireless_failcounter(network_id=config['meraki']['pytest']['network_id'], timespan=60*60)
    # for i in r.data:
    #     if '802.1X auth fail' in i['type']:
    #         print(i)
    #         s
        # print(i['type'])
        # s
    # print(r.data)
    # assert r.code == 0

def test_claim_device():
    serials = config['meraki']['pytest']['serials']
    r = meraki.claim_network_devices(network_id=config['meraki']['pytest']['network_id'], serials=serials)
    print(r)


if __name__ == '__main__':
    # test_get_network_events()
    # test_get_networks()
    # test_reboot_device()
    # test_get_alert()
    # print(meraki.get_network_id_by_name('45173'))
    test_get_wireless_failcounter()
    # test_claim_device()