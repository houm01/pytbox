#!/usr/bin/env python3


import os
from pytbox.feishu.client import Client as FeishuClient


feishu = FeishuClient(app_id=os.getenv("FEISHU_APP_ID"), app_secret=os.getenv("FEISHU_APP_SECRET"))


def test_feishu_send_message_notify():
    r = feishu.extensions.send_message_notify(title='test')
    assert r.code == 0

if __name__ == "__main__":
    pass
# print(r)