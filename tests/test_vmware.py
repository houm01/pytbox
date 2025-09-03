#!/usr/bin/env python3

from pytbox.base import vmware_test

r = vmware_test.get_vm_list()
print(r)