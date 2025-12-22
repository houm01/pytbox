#!/usr/bin/env python3


from pytbox.base import sls

r = sls.put_logs(
    level='INFO',
    msg='test',
    app='test',
    caller_filename='test',
    caller_lineno="1",
    caller_function='test',
    call_full_filename='test'
)

print(r)

