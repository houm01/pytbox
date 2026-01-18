from pytbox.base import get_aliyun


aliyun = get_aliyun()

# r = aliyun.ecs.list()
# print(r)


r = aliyun.cms.get_metric_data(
    namespace="acs_ecs_dashboard",
    metric_name="CPUUtilization",
    dimensions={"instanceId": "i-2ze6ob1a89m7ezcpdwbe"},
    last_minute=10,
)
print(r)