"""Aliyun RAM resource operations."""

from __future__ import annotations

from typing import Any

from alibabacloud_ram20150501 import models as ram_20150501_models
from alibabacloud_tea_util import models as util_models

from ...schemas.response import ReturnResponse


class RAMResource:
    """Aliyun RAM read-only resource wrapper."""

    def __init__(self, client: Any) -> None:
        """Initialize resource.

        Args:
            client: AliyunClient instance.
        """
        self._c = client

    @staticmethod
    def _body_to_map(response: Any) -> dict[str, Any]:
        """Convert SDK response body to map safely.

        Args:
            response: SDK response object.

        Returns:
            dict[str, Any]: Parsed map result.
        """
        body = getattr(response, "body", None)
        if body is None or not hasattr(body, "to_map"):
            return {}
        result = body.to_map()
        return result if isinstance(result, dict) else {}

    @staticmethod
    def _failure_response(error: Exception) -> ReturnResponse:
        """Build unified failure response.

        Args:
            error: Caught exception.

        Returns:
            ReturnResponse: Failure payload.
        """
        return ReturnResponse(code=1, msg="failed", data={"error": str(error)})

    def get_users(self) -> ReturnResponse:
        """Get RAM users.

        Returns:
            ReturnResponse: ``data`` contains ``total`` and ``users``.
        """
        try:
            request = ram_20150501_models.ListUsersRequest()
            runtime = util_models.RuntimeOptions()
            response = self._c.call(
                "ram_list_users",
                lambda: self._c.ram.list_users_with_options(request, runtime),
            )
            body_map = self._body_to_map(response)
            users = body_map.get("Users", {}).get("User", [])
            if not isinstance(users, list):
                users = []
            return ReturnResponse(code=0, msg="success", data={"total": len(users), "users": users})
        except Exception as error:  # noqa: BLE001
            return self._failure_response(error)

    def list_users(self) -> ReturnResponse:
        """Alias of ``get_users``.

        Returns:
            ReturnResponse: Same as ``get_users``.
        """
        return self.get_users()

    def get_access_keys(self, username: str | None = None) -> ReturnResponse:
        """Get RAM access keys.

        Args:
            username: Optional RAM username.

        Returns:
            ReturnResponse: ``data`` contains ``total`` and ``access_keys``.
        """
        try:
            request = ram_20150501_models.ListAccessKeysRequest(user_name=username)
            runtime = util_models.RuntimeOptions()
            response = self._c.call(
                "ram_list_access_keys",
                lambda: self._c.ram.list_access_keys_with_options(request, runtime),
            )
            body_map = self._body_to_map(response)
            access_keys = body_map.get("AccessKeys", {}).get("AccessKey", [])
            if not isinstance(access_keys, list):
                access_keys = []
            return ReturnResponse(
                code=0,
                msg="success",
                data={"total": len(access_keys), "access_keys": access_keys},
            )
        except Exception as error:  # noqa: BLE001
            return self._failure_response(error)

    def list_access_keys(self, username: str | None = None) -> ReturnResponse:
        """Alias of ``get_access_keys``.

        Args:
            username: Optional RAM username.

        Returns:
            ReturnResponse: Same as ``get_access_keys``.
        """
        return self.get_access_keys(username=username)

    def get_access_key_last_used(self, username: str, user_access_key_id: str) -> ReturnResponse:
        """Get RAM access key last-used timestamp.

        Args:
            username: RAM username.
            user_access_key_id: Access key id.

        Returns:
            ReturnResponse: ``data`` contains ``last_used``.
        """
        try:
            request = ram_20150501_models.GetAccessKeyLastUsedRequest(
                user_name=username,
                user_access_key_id=user_access_key_id,
            )
            runtime = util_models.RuntimeOptions()
            response = self._c.call(
                "ram_get_access_key_last_used",
                lambda: self._c.ram.get_access_key_last_used_with_options(request, runtime),
            )
            body_map = self._body_to_map(response)
            last_used = body_map.get("AccessKeyLastUsed", {}).get("LastUsedDate")
            return ReturnResponse(code=0, msg="success", data={"last_used": last_used})
        except Exception as error:  # noqa: BLE001
            return self._failure_response(error)

    def get_user_mfa_info(self, username: str) -> ReturnResponse:
        """Get RAM user MFA information.

        Args:
            username: RAM username.

        Returns:
            ReturnResponse: ``data`` contains ``mfa_info``.
        """
        try:
            request = ram_20150501_models.GetUserMFAInfoRequest(user_name=username)
            runtime = util_models.RuntimeOptions()
            response = self._c.call(
                "ram_get_user_mfa_info",
                lambda: self._c.ram.get_user_mfainfo_with_options(request, runtime),
            )
            body_map = self._body_to_map(response)
            return ReturnResponse(code=0, msg="success", data={"mfa_info": body_map.get("MFADevice")})
        except Exception as error:  # noqa: BLE001
            return self._failure_response(error)

    def get_user_info(self, username: str) -> ReturnResponse:
        """Get RAM user profile.

        Args:
            username: RAM username.

        Returns:
            ReturnResponse: ``data`` contains ``user_info``.
        """
        try:
            request = ram_20150501_models.GetUserRequest(user_name=username)
            runtime = util_models.RuntimeOptions()
            response = self._c.call(
                "ram_get_user_info",
                lambda: self._c.ram.get_user_with_options(request, runtime),
            )
            body_map = self._body_to_map(response)
            return ReturnResponse(code=0, msg="success", data={"user_info": body_map.get("User")})
        except Exception as error:  # noqa: BLE001
            return self._failure_response(error)

    def get_policy_for_user(self, username: str) -> ReturnResponse:
        """Get RAM policies attached to a user.

        Args:
            username: RAM username.

        Returns:
            ReturnResponse: ``data`` contains ``policy_for_user``.
        """
        try:
            request = ram_20150501_models.ListPoliciesForUserRequest(user_name=username)
            runtime = util_models.RuntimeOptions()
            response = self._c.call(
                "ram_list_policy_for_user",
                lambda: self._c.ram.list_policies_for_user_with_options(request, runtime),
            )
            body_map = self._body_to_map(response)
            policies = body_map.get("Policies", {}).get("Policy", [])
            if not isinstance(policies, list):
                policies = []
            return ReturnResponse(code=0, msg="success", data={"policy_for_user": policies})
        except Exception as error:  # noqa: BLE001
            return self._failure_response(error)

    def list_policy_for_user(self, username: str) -> ReturnResponse:
        """Alias of ``get_policy_for_user``.

        Args:
            username: RAM username.

        Returns:
            ReturnResponse: Same as ``get_policy_for_user``.
        """
        return self.get_policy_for_user(username=username)
