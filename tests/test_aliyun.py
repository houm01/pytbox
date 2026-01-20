from pytbox.base import get_aliyun, get_aliyun_tyun


# aliyun = get_aliyun()
aliyun = get_aliyun_tyun()

# r = aliyun.ecs.list()
# print(r)


# r = aliyun.cms.get_metric_data(
#     namespace="acs_ecs_dashboard",
#     metric_name="CPUUtilization",
#     dimensions={"instanceId": "i-2ze6ob1a89m7ezcpdwbe"},
#     last_minute=10,
# )
# print(r)

# r = aliyun.ram.list_users()
# # print(r)
# for user in r.data['users']:
#     print(user)
#     s
#     username = user['UserName']
#     r = aliyun.ram.list_access_keys(username=username)
#     print(r)
#     s

# r = aliyun.ram.list_access_keys()
# print(r)

# r = aliyun.ram.get_access_key_last_used(username='houmingming', user_access_key_id='LTAI5tDeyLCP2XqfuvnWvszt')
# print(r)

# r = aliyun.ram.get_user_mfa_info(username='houmingming')
# print(r)

# r = aliyun.ram.get_user_info(username='houmingming')
# print(r)
r = aliyun.ram.list_policy_for_user(username='houmingming')
print(r)