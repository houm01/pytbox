#!/usr/bin/env python3


from pytbox.base import ad_dev, ad_prod


r = ad_dev.list_user()
for i in r:
    print(type(i))
    s