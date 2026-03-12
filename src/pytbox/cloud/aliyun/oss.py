"""Aliyun OSS resource operations."""

from __future__ import annotations

from typing import Any

from alibabacloud_oss_v2 import models as oss_models

from ...schemas.response import ReturnResponse
from ._helpers import failure_response, serialize_sdk_value


class OSSResource:
    """Aliyun OSS read-only resource wrapper."""

    def __init__(self, client: Any) -> None:
        """Initialize resource.

        Args:
            client: AliyunClient instance.
        """
        self._c = client

    def list_buckets(self, *, page_size: int = 100, **kwargs: Any) -> ReturnResponse:
        """List OSS buckets."""
        try:
            marker = kwargs.pop("marker", None)
            buckets_all: list[dict[str, Any]] = []

            while True:
                request = oss_models.service.ListBucketsRequest(
                    marker=marker,
                    max_keys=page_size,
                    **kwargs,
                )
                response = self._c.call(
                    "oss_list_buckets",
                    lambda: self._c.oss.list_buckets(request),
                )
                buckets = serialize_sdk_value(getattr(response, "buckets", None))
                if not isinstance(buckets, list):
                    buckets = []
                buckets_all.extend([item for item in buckets if isinstance(item, dict)])

                if not getattr(response, "is_truncated", False):
                    break
                marker = getattr(response, "next_marker", None)
                if not marker:
                    break

            return ReturnResponse(code=0, msg="success", data=buckets_all)
        except Exception as error:  # noqa: BLE001
            return failure_response(error)

    def get_bucket_info(self, bucket_name: str) -> ReturnResponse:
        """Get OSS bucket metadata."""
        try:
            request = oss_models.bucket_basic.GetBucketInfoRequest(bucket=bucket_name)
            response = self._c.call(
                "oss_get_bucket_info",
                lambda: self._c.oss.get_bucket_info(request),
            )
            data = serialize_sdk_value(getattr(response, "bucket_info", None))
            return ReturnResponse(code=0, msg="success", data=data)
        except Exception as error:  # noqa: BLE001
            return failure_response(error)

    def get_bucket_acl(self, bucket_name: str) -> ReturnResponse:
        """Get OSS bucket ACL."""
        try:
            request = oss_models.bucket_basic.GetBucketAclRequest(bucket=bucket_name)
            response = self._c.call(
                "oss_get_bucket_acl",
                lambda: self._c.oss.get_bucket_acl(request),
            )
            return ReturnResponse(code=0, msg="success", data=serialize_sdk_value(response))
        except Exception as error:  # noqa: BLE001
            return failure_response(error)

    def get_bucket_versioning(self, bucket_name: str) -> ReturnResponse:
        """Get OSS bucket versioning status."""
        try:
            request = oss_models.bucket_basic.GetBucketVersioningRequest(bucket=bucket_name)
            response = self._c.call(
                "oss_get_bucket_versioning",
                lambda: self._c.oss.get_bucket_versioning(request),
            )
            return ReturnResponse(code=0, msg="success", data=serialize_sdk_value(response))
        except Exception as error:  # noqa: BLE001
            return failure_response(error)

    def get_bucket_encryption(self, bucket_name: str) -> ReturnResponse:
        """Get OSS bucket encryption configuration."""
        try:
            request = oss_models.bucket_encryption.GetBucketEncryptionRequest(bucket=bucket_name)
            response = self._c.call(
                "oss_get_bucket_encryption",
                lambda: self._c.oss.get_bucket_encryption(request),
            )
            return ReturnResponse(code=0, msg="success", data=serialize_sdk_value(response))
        except Exception as error:  # noqa: BLE001
            return failure_response(error)

    def get_bucket_logging(self, bucket_name: str) -> ReturnResponse:
        """Get OSS bucket access logging configuration."""
        try:
            request = oss_models.bucket_logging.GetBucketLoggingRequest(bucket=bucket_name)
            response = self._c.call(
                "oss_get_bucket_logging",
                lambda: self._c.oss.get_bucket_logging(request),
            )
            return ReturnResponse(code=0, msg="success", data=serialize_sdk_value(response))
        except Exception as error:  # noqa: BLE001
            return failure_response(error)
