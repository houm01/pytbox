#!/usr/bin/env python3

import os
from pytbox.victoriametrics import VictoriaMetrics


vm = VictoriaMetrics(url=os.getenv("VICTORIAMETRICS_URL", "http://localhost:8428"))

def test_query():
    r = vm.query('ping_average_response_ms')
    print(r)


if __name__ == "__main__":
    test_query()
