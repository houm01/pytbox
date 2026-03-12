"""Aliyun Security Center resource operations."""

from __future__ import annotations

from typing import Any

from alibabacloud_sas20181203 import models as sas_models
from alibabacloud_tea_util import models as util_models

from ...schemas.response import ReturnResponse
from ._helpers import body_to_map, extract_total, failure_response


class SASResource:
    """Aliyun Security Center read-only resource wrapper."""

    def __init__(self, client: Any) -> None:
        """Initialize resource.

        Args:
            client: AliyunClient instance.
        """
        self._c = client

    def list_alerts(self, *, page_size: int = 50, **kwargs: Any) -> ReturnResponse:
        """List Security Center baseline alerts."""
        try:
            current_page = 1
            alerts_all: list[dict[str, Any]] = []
            runtime = util_models.RuntimeOptions()

            while True:
                request = sas_models.DescribeCheckWarningsRequest(
                    current_page=current_page,
                    page_size=page_size,
                    **kwargs,
                )
                response = self._c.call(
                    "sas_list_alerts",
                    lambda: self._c.sas.describe_check_warnings_with_options(request, runtime),
                )
                body_map = body_to_map(response)
                items = body_map.get("CheckWarnings") or []
                if not isinstance(items, list):
                    items = []
                items = [item for item in items if isinstance(item, dict)]
                if not items:
                    break
                alerts_all.extend(items)

                total_count = extract_total(body_map, "TotalCount")
                if total_count is not None:
                    if current_page * page_size >= total_count:
                        break
                elif len(items) < page_size:
                    break
                current_page += 1

            return ReturnResponse(code=0, msg="success", data=alerts_all)
        except Exception as error:  # noqa: BLE001
            return failure_response(error)
