#!/usr/bin/env python3

from pytbox.base import feishu


def test_feishu_send_message_notify():
    r = feishu.extensions.send_message_notify(title='test')
    assert r.code == 0

if __name__ == "__main__":
    test_feishu_send_message_notify()