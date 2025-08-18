#!/usr/bin/env python3


from pytbox.onepassword_connect import OnePasswordConnect


oc = OnePasswordConnect(vault_id="hcls5uxuq5dmxorw6rfewefdsa")

# r = oc.create_item()
# print(r)

# r = oc.search_item(tag='lululemon')
r = oc.update_item(item_id="xm2a67hysuw2emasp325i7dyki", name="demo_update3", username="demo03", password="password03", notes="notes03", tags=['test03'])
print(r)

