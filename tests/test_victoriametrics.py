#!/usr/bin/env python3

from pytbox.base import vm



def test_query():
    r = vm.query('ping_average_response_ms')
    print(r)

def test_get_labels():
    r = vm.get_labels('ping_average_response_ms')
    print(r)

if __name__ == "__main__":
    test_get_labels()
