from pytbox.base import get_aliyun


aliyun = get_aliyun()

r = aliyun.ecs.list()
print(r)
