#!/usr/bin/env python3


from pytbox.onepassword_connect import OnePasswordConnect


oc = OnePasswordConnect(vault_id="hcls5uxuq5dmxorw6rfewefdsa")

def test_get_item():
    r = oc.get_item(item_id="f7eda4fgxfcukna7tpdpw7frlu")
    print(r)

test_get_item()