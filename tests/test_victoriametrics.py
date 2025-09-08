#!/usr/bin/env python3

from pytbox.base import vm



def test_query():
    r = vm.query('ping_average_response_ms')
    print(r)

def test_check_ping_result():
    r = vm.check_ping_result(target='121.46.237.186', last_minute=10)
    print(r)

def test_get_labels():
    r = vm.get_labels('ping_average_response_ms')
    print(r)

def test_check_snmp_port_status():
    r = vm.check_snmp_port_status(sysname="shylf-prod-coresw-ce6820-182", if_name="10GE1/0/47", last_minute=10)
    print(r)

if __name__ == "__main__":
    # test_get_labels()
    # test_query()
    # test_check_ping_result()
    test_check_snmp_port_status()
