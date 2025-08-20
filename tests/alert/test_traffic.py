#!/usr/bin/env python3


from pytbox.base import vm, config



def test_trigger():
    for item in config['alert']['trigger']['traffic']['items']:
        r = vm.check_interface_rate(direction=item['direction'], sysName=item['sysname'], ifName=item['if_name'], last_minutes=item['last_minute'])
        assert isinstance(r, int)


if __name__ == "__main__":
    test_trigger()
    