
from typing import Optional
from ...utils.response import ReturnResponse
from alibabacloud_ram20150501 import models as ram_20150501_models
from alibabacloud_tea_util import models as util_models


class RAMResource:
    def __init__(self, client):
        self._c = client

    def get_users(self) -> ReturnResponse:
        list_user_request = ram_20150501_models.ListUsersRequest()
        runtime = util_models.RuntimeOptions()
        r = self._c.call(
            'ram_list_users',
            lambda: self._c.ram.list_users_with_options(list_user_request, runtime)
        )
        try:
            users = r.body.to_map()['Users']['User']
            return ReturnResponse(
                code=0, 
                msg='success', 
                data={
                    'total': len(users),
                    'users': users
                }
            )
        except Exception as e:
            return ReturnResponse(
                code=1,
                msg='failed',
                data={
                    'result': r,
                    'error': str(e)
                }
            )
    
    def get_access_keys(self, username: str=None) -> ReturnResponse:
        '''
        最好传入 username, 否则输出的 accesskey 不包含用户名, 也就不知道是在哪个用户创建的
        在调用这个接口之前, 先调用 list_users 接口, 获取到 username
        
        Args:
            username (str, optional): _description_. Defaults to None.

        Returns:
            _type_: _description_
        '''
        list_access_key_request = ram_20150501_models.ListAccessKeysRequest(
            user_name=username
        )
        runtime = util_models.RuntimeOptions()
        r = self._c.call(
            'ram_list_access_keys',
            lambda: self._c.ram.list_access_keys_with_options(list_access_key_request, runtime)
        )
        try:
            access_keys = r.body.to_map()['AccessKeys']['AccessKey']
            return ReturnResponse(
                code=0,
                msg='success',
                data={
                    'total': len(access_keys),
                    'access_keys': access_keys
                }
            )
        except Exception as e:
            return ReturnResponse(
                code=1,
                msg='failed',
                data={
                    'result': r,
                    'error': str(e)
                }
            )
    
    def get_access_key_last_used(self, username, user_access_key_id) -> ReturnResponse:
        get_access_key_last_used_request = ram_20150501_models.GetAccessKeyLastUsedRequest(
            user_name=username,
            user_access_key_id=user_access_key_id
        )
        runtime = util_models.RuntimeOptions()
        r = self._c.call(
            'ram_get_access_key_last_used',
            lambda: self._c.ram.get_access_key_last_used_with_options(get_access_key_last_used_request, runtime)
        )
        try:
            last_used = r.body.to_map()['AccessKeyLastUsed']['LastUsedDate']
            return ReturnResponse(
                code=0,
                msg='success',
                data={
                    'last_used': last_used
                }
            )
        except Exception as e:
            return ReturnResponse(
                code=1,
                msg='failed',
                data={
                    'result': r,
                    'error': str(e)
                }
            )
    
    def get_user_mfa_info(self, username) -> ReturnResponse:
        get_user_mfa_info_request = ram_20150501_models.GetUserMFAInfoRequest(
            user_name=username
        )
        runtime = util_models.RuntimeOptions()
        r = self._c.call(
            'ram_get_user_mfa_info',
            lambda: self._c.ram.get_user_mfainfo_with_options(get_user_mfa_info_request, runtime)
        )
        try:
            mfa_info = r.body.to_map()['MFADevice']
            return ReturnResponse(
                code=0,
                msg='success',
                data={
                    'mfa_info': mfa_info
                }
            )
        except Exception as e:
            return ReturnResponse(
                code=1,
                msg='failed',
            )
    
    def get_user_info(self, username) -> ReturnResponse:
        get_user_info_request = ram_20150501_models.GetUserRequest(
            user_name=username
        )
        runtime = util_models.RuntimeOptions()
        r = self._c.call(
            'ram_get_user_info',
            lambda: self._c.ram.get_user_with_options(get_user_info_request, runtime)
        )
        try:
            user_info = r.body.to_map()['User']
            return ReturnResponse(
                code=0,
                msg='success',
                data={
                    'user_info': user_info
                }
            )
        except Exception as e:
            return ReturnResponse(
                code=1,
                msg='failed',
                data={
                    'result': r,
                    'error': str(e)
                }
            )
    
    def get_policy_for_user(self, username) -> ReturnResponse:
        list_policy_for_user_request = ram_20150501_models.ListPoliciesForUserRequest(
            user_name=username
        )
        runtime = util_models.RuntimeOptions()
        r = self._c.call(
            'ram_list_policy_for_user',
            lambda: self._c.ram.list_policies_for_user_with_options(list_policy_for_user_request, runtime)
        )
        try:
            policy_for_user = r.body.to_map()['Policies']['Policy']
            return ReturnResponse(
                code=0,
                msg='success',
                data={
                    'policy_for_user': policy_for_user
                }
            )
        except Exception as e:
            return ReturnResponse(
                code=1,
                msg='failed',
                data={
                    'result': r,
                    'error': str(e)
                }
            )