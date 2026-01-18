import time
from pytbox.base import get_volc

volc = get_volc()

# r = volc.ecs.list()
# print(r)

r = volc.cloudmonitor.get_metric_data(
    namespace="VCM_ECS",
    sub_namespace="Instance",
    metric_name="CpuTotal",
    dimensions={"ResourceID": "i-ye837dh2ios6ipm6hl01"},
    last_minute=5,
)
print(r)