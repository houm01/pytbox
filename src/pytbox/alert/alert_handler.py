#!/usr/bin/env python3

"""Alert delivery orchestration with detailed per-channel results."""

from __future__ import annotations

import datetime
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from ..database.mongo import Mongo
from ..dida365 import Dida365
from ..feishu.client import Client as FeishuClient
from ..mail.client import MailClient
from ..schemas.codes import RespCode
from ..schemas.response import ReturnResponse
from ..utils.timeutils import TimeUtils

logger = logging.getLogger(__name__)


PRIORITY_TO_FEISHU: dict[str, str] = {
    "critical": "P0",
    "high": "P1",
    "warning": "P2",
}


class AlertDeliveryError(RuntimeError):
    """Raised when one or more enabled channels fail to deliver."""

    def __init__(self, response: ReturnResponse) -> None:
        """Initialize delivery error.

        Args:
            response: Aggregated failure response.
        """
        super().__init__(response.msg)
        self.response = response


@dataclass
class ChannelResult:
    """Delivery status of one channel."""

    enabled: bool
    attempted: bool = False
    ok: Optional[bool] = None
    action: Optional[str] = None
    error: Optional[str] = None
    data: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize channel status.

        Returns:
            dict[str, Any]: Plain dictionary used in API responses.
        """
        return {
            "enabled": self.enabled,
            "attempted": self.attempted,
            "ok": self.ok,
            "action": self.action,
            "error": self.error,
            "data": self.data,
        }


@dataclass
class AlertSendResult:
    """Aggregated status across all alert delivery channels."""

    event_id: str
    event_type: str
    skipped: bool = False
    reason: Optional[str] = None
    mongo: ChannelResult = field(default_factory=lambda: ChannelResult(enabled=True))
    feishu: ChannelResult = field(default_factory=lambda: ChannelResult(enabled=False))
    mail: ChannelResult = field(default_factory=lambda: ChannelResult(enabled=False))
    dida: ChannelResult = field(default_factory=lambda: ChannelResult(enabled=False))
    wecom: ChannelResult = field(default_factory=lambda: ChannelResult(enabled=False))

    def failed_channels(self) -> list[str]:
        """Return failed channel names.

        Returns:
            list[str]: Channel list where delivery was attempted and failed.
        """
        failed: list[str] = []
        for name, channel in self.channels().items():
            if channel.enabled and channel.attempted and channel.ok is False:
                failed.append(name)
        return failed

    def channels(self) -> dict[str, ChannelResult]:
        """Return all channel status objects.

        Returns:
            dict[str, ChannelResult]: All channel status objects.
        """
        return {
            "mongo": self.mongo,
            "feishu": self.feishu,
            "dida": self.dida,
            "mail": self.mail,
            "wecom": self.wecom,
        }

    def to_payload(self) -> dict[str, Any]:
        """Serialize the aggregate result into response payload.

        Returns:
            dict[str, Any]: Structured response payload.
        """
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "skipped": self.skipped,
            "reason": self.reason,
            "channels": {
                name: channel.to_dict() for name, channel in self.channels().items()
            },
            "failed_channels": self.failed_channels(),
        }


class AlertHandler:
    """AlertHandler class.

    This class orchestrates persistence and optional downstream channel delivery.
    """

    def __init__(
        self,
        config: Optional[dict[str, Any]] = None,
        mongo_client: Optional[Mongo] = None,
        feishu_client: Optional[FeishuClient] = None,
        dida_client: Optional[Dida365] = None,
        mail_client: Optional[MailClient] = None,
        env: Literal["dev", "prod"] = "prod",
    ) -> None:
        """Initialize AlertHandler.

        Args:
            config: Runtime config dict.
            mongo_client: Mongo client, required.
            feishu_client: Optional Feishu client.
            dida_client: Optional Dida client.
            mail_client: Optional mail client.
            env: Runtime environment.

        Raises:
            ValueError: If mongo client is missing.
        """
        if mongo_client is None:
            raise ValueError("mongo_client is required")

        self.config = config or {}
        self.mongo = mongo_client
        self.feishu = feishu_client
        self.dida = dida_client
        self.mail = mail_client
        self.env = env

    def send_alert(
        self,
        event_id: Optional[str] = None,
        event_type: Literal["trigger", "resolved"] = "trigger",
        event_time: datetime.datetime | str | None = None,
        event_name: Optional[str] = None,
        event_content: Optional[str] = None,
        entity_name: Optional[str] = None,
        priority: Literal["critical", "high", "warning"] = "high",
        resolved_expr: Optional[dict[str, Any]] = None,
        suggestion: str = "",
        troubleshot: str = "暂无",
        actions: Optional[str] = None,
        history: Optional[str] = None,
        mongo_id: Any = None,
        event_description: Optional[str] = None,
    ) -> ReturnResponse:
        """Send one alert event.

        Args:
            event_id: Event identifier. Auto-generated when absent.
            event_type: Event type, `trigger` or `resolved`.
            event_time: Event time as datetime or string.
            event_name: Event name.
            event_content: Event content.
            entity_name: Related entity name.
            priority: Alert priority.
            resolved_expr: Resolver payload used for trigger event persistence.
            suggestion: Suggestion field.
            troubleshot: Troubleshooting hint.
            actions: Custom action text for Feishu card.
            history: Custom history text.
            mongo_id: Mongo `_id` used by resolved event.
            event_description: Event description text.

        Returns:
            ReturnResponse: Detailed channel delivery result.

        Raises:
            ValueError: Invalid input or channel configuration.
            AlertDeliveryError: Any enabled channel failed.
        """
        self._validate_inputs(
            event_type=event_type,
            event_name=event_name,
            event_content=event_content,
            entity_name=entity_name,
            mongo_id=mongo_id,
            event_time=event_time,
        )

        event_id_value = event_id or str(uuid.uuid4())
        event_time_value = event_time or TimeUtils.get_now_time_mongo()

        result = AlertSendResult(
            event_id=event_id_value,
            event_type=event_type,
            mongo=ChannelResult(enabled=True),
            feishu=ChannelResult(
                enabled=self._resolve_optional_channel_enabled(
                    channel_name="feishu",
                    enable_key="enable_alert",
                    client=self.feishu,
                    required_keys=["receive_id"],
                )
            ),
            mail=ChannelResult(
                enabled=self._resolve_optional_channel_enabled(
                    channel_name="mail",
                    enable_key="enable_mail",
                    client=self.mail,
                    required_keys=["mail_address", "subject_trigger", "subject_resolved"],
                )
            ),
            dida=ChannelResult(
                enabled=self._resolve_optional_channel_enabled(
                    channel_name="dida",
                    enable_key="enable_alert",
                    client=self.dida,
                    required_keys=["alert_project_id"],
                )
            ),
            wecom=ChannelResult(
                enabled=bool(self._channel_config("wecom").get("enable", False))
            ),
        )

        if not self.mongo.check_alarm_exist(
            event_type=event_type,
            event_content=event_content,
        ):
            result.skipped = True
            result.reason = "duplicate unresolved alert skipped"
            return ReturnResponse.no_data(
                msg="重复未恢复告警已跳过",
                data=result.to_payload(),
            )

        alarm_time = event_time_value
        self._run_mongo_step(
            result=result,
            event_type=event_type,
            event_id=event_id_value,
            event_time=event_time_value,
            event_name=event_name,
            event_content=event_content,
            entity_name=entity_name,
            priority=priority,
            resolved_expr=resolved_expr,
            suggestion=suggestion,
            troubleshot=troubleshot,
            mongo_id=mongo_id,
        )
        if event_type == "resolved":
            alarm_time = self._resolve_alarm_time_for_resolved(
                mongo_id=mongo_id,
                fallback=event_time_value,
            )

        history_text = history if history is not None else self._safe_recent_alerts(
            event_content=event_content
        )
        content = self._build_alert_content(
            event_name=event_name,
            event_type=event_type,
            event_time=event_time_value,
            alarm_time=alarm_time,
            event_content=event_content,
            entity_name=entity_name,
            suggestion=suggestion,
            troubleshot=troubleshot,
            history=history_text,
        )

        if result.feishu.enabled:
            self._run_feishu_step(
                result=result,
                event_type=event_type,
                event_content=event_content,
                event_name=event_name,
                entity_name=entity_name,
                event_time=event_time_value,
                alarm_time=alarm_time,
                event_description=event_description,
                actions=actions,
                troubleshot=troubleshot,
                history=history_text,
                priority=priority,
            )

        if result.mail.enabled:
            self._run_mail_step(
                result=result,
                event_type=event_type,
                event_id=event_id_value,
                event_content=event_content,
                event_name=event_name,
                entity_name=entity_name,
                event_time=event_time_value,
                priority=priority,
                troubleshot=troubleshot,
                suggestion=suggestion,
            )

        if result.dida.enabled:
            self._run_dida_step(
                result=result,
                event_type=event_type,
                event_id=event_id_value,
                event_time=event_time_value,
                event_content=event_content,
                content=content,
                priority=priority,
                mongo_id=mongo_id,
            )

        if result.wecom.enabled:
            result.wecom.data = {"message": "wecom channel is not implemented"}

        payload = result.to_payload()
        if payload["failed_channels"]:
            response = ReturnResponse.fail(
                code=RespCode.INTERNAL_ERROR,
                msg=(
                    "alert delivery failed: "
                    + ", ".join(payload["failed_channels"])
                ),
                data=payload,
            )
            raise AlertDeliveryError(response=response)

        return ReturnResponse.ok(data=payload, msg="alert sent")

    def _validate_inputs(
        self,
        event_type: str,
        event_name: Optional[str],
        event_content: Optional[str],
        entity_name: Optional[str],
        mongo_id: Any,
        event_time: datetime.datetime | str | None,
    ) -> None:
        """Validate public input arguments.

        Args:
            event_type: Event type.
            event_name: Event name.
            event_content: Event content.
            entity_name: Entity name.
            mongo_id: Mongo identifier.
            event_time: Event time value.

        Raises:
            ValueError: When any required field is invalid.
        """
        if event_type not in {"trigger", "resolved"}:
            raise ValueError("event_type must be 'trigger' or 'resolved'")

        required_fields = {
            "event_name": event_name,
            "event_content": event_content,
            "entity_name": entity_name,
        }
        missing = [name for name, value in required_fields.items() if not value]
        if missing:
            raise ValueError(f"missing required fields: {', '.join(missing)}")

        if event_type == "resolved" and mongo_id is None:
            raise ValueError("mongo_id is required for resolved event")

        if event_time is not None and not isinstance(
            event_time, (datetime.datetime, str)
        ):
            raise ValueError("event_time must be datetime, str, or None")

    def _channel_config(self, channel_name: str) -> dict[str, Any]:
        """Return one channel config block.

        Args:
            channel_name: Channel key in root config.

        Returns:
            dict[str, Any]: Channel config dictionary.
        """
        channel_cfg = self.config.get(channel_name, {})
        if isinstance(channel_cfg, dict):
            return channel_cfg
        return {}

    def _resolve_optional_channel_enabled(
        self,
        channel_name: str,
        enable_key: str,
        client: Any,
        required_keys: list[str],
    ) -> bool:
        """Resolve whether an optional channel is enabled.

        Args:
            channel_name: Channel name.
            enable_key: Enable flag key in config.
            client: Channel client instance.
            required_keys: Required config keys when enabled.

        Returns:
            bool: True when channel should run.

        Raises:
            ValueError: If enabled but client/config is incomplete.
        """
        channel_cfg = self._channel_config(channel_name)
        explicit_enabled = channel_cfg.get(enable_key)

        if explicit_enabled is False:
            return False

        if explicit_enabled is True and client is None:
            raise ValueError(f"{channel_name} client is required when {enable_key}=true")

        enabled = client is not None and explicit_enabled is not False
        if not enabled:
            return False

        missing_keys = [key for key in required_keys if not channel_cfg.get(key)]
        if missing_keys:
            raise ValueError(
                f"{channel_name} config missing required keys: {', '.join(missing_keys)}"
            )
        return True

    def _build_alert_content(
        self,
        event_name: str,
        event_type: str,
        event_time: datetime.datetime | str,
        alarm_time: datetime.datetime | str,
        event_content: str,
        entity_name: str,
        suggestion: str,
        troubleshot: str,
        history: str,
    ) -> list[str]:
        """Build unified card/task content lines.

        Args:
            event_name: Event name.
            event_type: Event type.
            event_time: Event time.
            alarm_time: Trigger time for resolved event.
            event_content: Event content.
            entity_name: Entity name.
            suggestion: Suggestion text.
            troubleshot: Troubleshooting text.
            history: History text.

        Returns:
            list[str]: Markdown lines.
        """
        content = [
            f"**事件名称**: {event_name}",
            (
                "**告警时间**: "
                + (
                    self._format_time(event_time, timezone_offset=0)
                    if event_type == "trigger"
                    else self._format_time(alarm_time, timezone_offset=8)
                )
            ),
            (
                "**事件内容**: "
                + (f"{event_content} 已恢复" if event_type == "resolved" else event_content)
            ),
            f"**告警实例**: {entity_name}",
            f"**建议**: {suggestion}",
            f"**故障排查**: {troubleshot}",
            f"**历史告警**: {history}",
        ]
        if event_type == "resolved":
            content.insert(
                2,
                f"**恢复时间**: {self._format_time(event_time, timezone_offset=0)}",
            )
        return content

    def _run_mongo_step(
        self,
        result: AlertSendResult,
        event_type: str,
        event_id: str,
        event_time: datetime.datetime | str,
        event_name: str,
        event_content: str,
        entity_name: str,
        priority: str,
        resolved_expr: Optional[dict[str, Any]],
        suggestion: str,
        troubleshot: str,
        mongo_id: Any,
    ) -> None:
        """Persist alert event into Mongo.

        Args:
            result: Aggregate channel result.
            event_type: Event type.
            event_id: Event identifier.
            event_time: Event time.
            event_name: Event name.
            event_content: Event content.
            entity_name: Entity name.
            priority: Priority text.
            resolved_expr: Resolve expression payload.
            suggestion: Suggestion text.
            troubleshot: Troubleshooting text.
            mongo_id: Mongo identifier for resolved update.
        """
        channel = result.mongo
        channel.attempted = True
        channel.action = "insert" if event_type == "trigger" else "update"

        started_at = time.monotonic()
        step_result = "ok"
        try:
            if event_type == "trigger":
                insert_result = self.mongo.collection.insert_one(
                    {
                        "event_id": event_id,
                        "event_type": event_type,
                        "event_name": event_name,
                        "event_time": event_time,
                        "event_content": event_content,
                        "entity_name": entity_name,
                        "priority": priority,
                        "resolved_expr": resolved_expr,
                        "suggestion": suggestion,
                        "troubleshot": troubleshot,
                    }
                )
                channel.ok = True
                channel.data = {"inserted_id": str(insert_result.inserted_id)}
                return

            update_result = self.mongo.collection.update_one(
                {"_id": mongo_id},
                {"$set": {"resolved_time": event_time}},
            )
            channel.ok = True
            channel.data = {
                "matched": getattr(update_result, "matched_count", None),
                "modified": getattr(update_result, "modified_count", None),
            }
        except Exception as exc:
            channel.ok = False
            channel.error = str(exc)
            step_result = "exception"
        finally:
            self._log_step(
                target=f"mongo.{channel.action}",
                result=step_result if channel.ok is not False else "failed",
                started_at=started_at,
            )

    def _resolve_alarm_time_for_resolved(
        self,
        mongo_id: Any,
        fallback: datetime.datetime | str,
    ) -> datetime.datetime | str:
        """Load original alarm time for resolved event display.

        Args:
            mongo_id: Mongo document id.
            fallback: Fallback time when document is missing.

        Returns:
            datetime.datetime | str: Alarm trigger time or fallback.
        """
        started_at = time.monotonic()
        try:
            alarm_doc = self.mongo.collection.find_one(
                {"_id": mongo_id},
                {"event_time": 1},
            )
            alarm_time = alarm_doc.get("event_time") if alarm_doc else fallback
            self._log_step("mongo.find_alarm_time", "ok", started_at)
            return alarm_time or fallback
        except Exception as exc:
            self._log_step("mongo.find_alarm_time", "exception", started_at)
            logger.warning("load alarm time failed: %s", exc)
            return fallback

    def _run_feishu_step(
        self,
        result: AlertSendResult,
        event_type: str,
        event_content: str,
        event_name: str,
        entity_name: str,
        event_time: datetime.datetime | str,
        alarm_time: datetime.datetime | str,
        event_description: Optional[str],
        actions: Optional[str],
        troubleshot: str,
        history: str,
        priority: str,
    ) -> None:
        """Deliver alert card via Feishu.

        Args:
            result: Aggregate channel result.
            event_type: Event type.
            event_content: Event content.
            event_name: Event name.
            entity_name: Entity name.
            event_time: Event time.
            alarm_time: Alarm trigger time.
            event_description: Optional description.
            actions: Optional custom actions text.
            troubleshot: Troubleshooting text.
            history: Historical alerts text.
            priority: Priority text.
        """
        channel = result.feishu
        channel.attempted = True
        channel.action = "send_alert_notify"

        started_at = time.monotonic()
        step_result = "ok"
        try:
            if event_type == "trigger":
                alarm_time_text = self._format_time(event_time, timezone_offset=0)
                resolved_time_text = None
            else:
                alarm_time_text = self._format_time(alarm_time, timezone_offset=8)
                resolved_time_text = self._format_time(event_time, timezone_offset=0)

            response = self.feishu.extensions.send_alert_notify(
                event_content=event_content,
                event_name=event_name,
                entity_name=entity_name,
                event_time=alarm_time_text,
                resolved_time=resolved_time_text,
                event_description=event_description,
                actions=actions if actions is not None else troubleshot,
                history=history,
                color="red" if event_type == "trigger" else "green",
                priority=self._feishu_priority(priority),
                receive_id=self._channel_config("feishu")["receive_id"],
            )
            if isinstance(response, ReturnResponse):
                channel.data = {
                    "code": response.code,
                    "msg": response.msg,
                    "data": response.data,
                }
                if response.code == int(RespCode.OK):
                    channel.ok = True
                else:
                    channel.ok = False
                    channel.error = response.msg
            else:
                channel.ok = True
                channel.data = response
        except Exception as exc:
            channel.ok = False
            channel.error = str(exc)
            step_result = "exception"
        finally:
            self._log_step(
                target="feishu.send_alert_notify",
                result=step_result if channel.ok is not False else "failed",
                started_at=started_at,
            )

    def _run_mail_step(
        self,
        result: AlertSendResult,
        event_type: str,
        event_id: str,
        event_content: str,
        event_name: str,
        entity_name: str,
        event_time: datetime.datetime | str,
        priority: str,
        troubleshot: str,
        suggestion: str,
    ) -> None:
        """Send alert mail.

        Args:
            result: Aggregate channel result.
            event_type: Event type.
            event_id: Event identifier.
            event_content: Event content.
            event_name: Event name.
            entity_name: Entity name.
            event_time: Event time.
            priority: Priority text.
            troubleshot: Troubleshooting text.
            suggestion: Suggestion text.
        """
        channel = result.mail
        channel.attempted = True
        channel.action = "send_mail"
        mail_config = self._channel_config("mail")

        started_at = time.monotonic()
        step_result = "ok"
        try:
            if event_type == "trigger":
                subject = f"{mail_config['subject_trigger']}, {event_content}"
                alarm_time = str(event_time)
            else:
                subject = f"{mail_config['subject_resolved']}, {event_content}"
                alarm_time = str(TimeUtils.get_now_time_mongo())

            response = self.mail.send_mail(
                receiver=[mail_config["mail_address"]],
                subject=subject,
                contents=(
                    f"event_content:{event_content}, alarm_time: {alarm_time}, "
                    f"event_id: {event_id}, alarm_name: {event_name}, entity_name: {entity_name}, "
                    f"priority: {priority}, automate_ts: {troubleshot}, suggestion: {suggestion}"
                ),
            )
            channel.data = response
            channel.ok = bool(response)
            if not channel.ok:
                channel.error = "mail send returned False"
        except Exception as exc:
            channel.ok = False
            channel.error = str(exc)
            step_result = "exception"
        finally:
            self._log_step(
                target="mail.send_mail",
                result=step_result if channel.ok is not False else "failed",
                started_at=started_at,
            )

    def _run_dida_step(
        self,
        result: AlertSendResult,
        event_type: str,
        event_id: str,
        event_time: datetime.datetime | str,
        event_content: str,
        content: list[str],
        priority: str,
        mongo_id: Any,
    ) -> None:
        """Create or update Dida task.

        Args:
            result: Aggregate channel result.
            event_type: Event type.
            event_id: Event id.
            event_time: Event time.
            event_content: Event content.
            content: Markdown lines used by task body.
            priority: Priority text.
            mongo_id: Mongo document id.
        """
        channel = result.dida
        channel.attempted = True
        channel.action = "task_create" if event_type == "trigger" else "task_update_complete"
        dida_config = self._channel_config("dida")

        started_at = time.monotonic()
        step_result = "ok"
        try:
            if event_type == "trigger":
                create_resp = self.dida.task_create(
                    project_id=dida_config["alert_project_id"],
                    title=event_content,
                    content="\n".join(content),
                    tags=["L-监控告警", priority],
                )
                task_id = self._extract_task_id(create_resp)
                channel.data = {
                    "create_response": self._normalize_external_response(create_resp),
                    "task_id": task_id,
                }
                if not self._response_ok(create_resp):
                    channel.ok = False
                    channel.error = self._response_error_message(create_resp)
                    return

                channel.ok = True
                if task_id:
                    self.mongo.collection.update_one(
                        {"event_id": event_id},
                        {"$set": {"dida_task_id": task_id}},
                    )
                return

            task_id = self._load_dida_task_id(mongo_id=mongo_id)
            if not task_id:
                channel.ok = True
                channel.data = {"task_id": None, "updated": False}
                return

            update_resp = self.dida.task_update(
                task_id=task_id,
                project_id=dida_config["alert_project_id"],
                content=(
                    "\n**恢复时间**: "
                    f"{self._format_time(event_time, timezone_offset=0)}"
                ),
            )
            complete_resp = self.dida.task_complete(
                task_id=task_id,
                project_id=dida_config["alert_project_id"],
            )
            channel.data = {
                "task_id": task_id,
                "update_response": self._normalize_external_response(update_resp),
                "complete_response": self._normalize_external_response(complete_resp),
            }
            if not self._response_ok(update_resp):
                channel.ok = False
                channel.error = (
                    "dida task_update failed: "
                    + self._response_error_message(update_resp)
                )
                return
            if not self._response_ok(complete_resp):
                channel.ok = False
                channel.error = (
                    "dida task_complete failed: "
                    + self._response_error_message(complete_resp)
                )
                return
            channel.ok = True
        except Exception as exc:
            channel.ok = False
            channel.error = str(exc)
            step_result = "exception"
        finally:
            self._log_step(
                target=f"dida.{channel.action}",
                result=step_result if channel.ok is not False else "failed",
                started_at=started_at,
            )

    def _load_dida_task_id(self, mongo_id: Any) -> Optional[str]:
        """Load dida task id from mongo document.

        Args:
            mongo_id: Mongo document id.

        Returns:
            Optional[str]: Existing Dida task id.
        """
        started_at = time.monotonic()
        try:
            doc = self.mongo.collection.find_one({"_id": mongo_id}, {"dida_task_id": 1})
            self._log_step("mongo.find_dida_task_id", "ok", started_at)
            if isinstance(doc, dict):
                value = doc.get("dida_task_id")
                return str(value) if value else None
            return None
        except Exception as exc:
            self._log_step("mongo.find_dida_task_id", "exception", started_at)
            logger.warning("load dida task id failed: %s", exc)
            return None

    def _safe_recent_alerts(self, event_content: str) -> str:
        """Fetch recent alerts with safe fallback.

        Args:
            event_content: Event content key.

        Returns:
            str: History text.
        """
        started_at = time.monotonic()
        try:
            value = self.mongo.recent_alerts(event_content=event_content)
            self._log_step("mongo.recent_alerts", "ok", started_at)
            return value
        except Exception as exc:
            self._log_step("mongo.recent_alerts", "exception", started_at)
            logger.warning("recent alerts unavailable: %s", exc)
            return "历史告警获取失败"

    def _response_ok(self, value: Any) -> bool:
        """Check whether an external response means success.

        Args:
            value: External call return value.

        Returns:
            bool: Success flag.
        """
        if isinstance(value, ReturnResponse):
            return value.code == int(RespCode.OK)
        if isinstance(value, bool):
            return value
        return value is not None

    def _response_error_message(self, value: Any) -> str:
        """Build a human-readable error message for external response.

        Args:
            value: External response.

        Returns:
            str: Error message.
        """
        if isinstance(value, ReturnResponse):
            return value.msg
        return "unexpected channel response"

    def _normalize_external_response(self, value: Any) -> Any:
        """Normalize external responses for response payload.

        Args:
            value: External response object.

        Returns:
            Any: Serializable payload.
        """
        if isinstance(value, ReturnResponse):
            return {
                "code": value.code,
                "msg": value.msg,
                "data": value.data,
            }
        return value

    def _extract_task_id(self, create_resp: Any) -> Optional[str]:
        """Extract Dida task id from create response.

        Args:
            create_resp: Response from task_create.

        Returns:
            Optional[str]: Task id if available.
        """
        if isinstance(create_resp, ReturnResponse):
            data = create_resp.data
            if isinstance(data, dict) and data.get("id"):
                return str(data["id"])
            return None

        data = getattr(create_resp, "data", None)
        if isinstance(data, dict) and data.get("id"):
            return str(data["id"])
        return None

    def _feishu_priority(self, priority: str) -> str:
        """Map internal priority to Feishu card priority.

        Args:
            priority: Internal priority value.

        Returns:
            str: Feishu priority text.
        """
        return PRIORITY_TO_FEISHU.get(priority, "P2")

    def _format_time(
        self,
        value: datetime.datetime | str,
        timezone_offset: int,
    ) -> str:
        """Format datetime/string value as display time.

        Args:
            value: Datetime or already-formatted string.
            timezone_offset: Offset used by TimeUtils.

        Returns:
            str: Display time string.
        """
        if isinstance(value, datetime.datetime):
            converted = TimeUtils.convert_timeobj_to_str(
                timeobj=value,
                timezone_offset=timezone_offset,
            )
            return converted or str(value)
        return str(value)

    def _log_step(self, target: str, result: str, started_at: float) -> None:
        """Write key-step reliability log.

        Args:
            target: Step target identifier.
            result: Step result summary.
            started_at: Monotonic start time.
        """
        duration_ms = int((time.monotonic() - started_at) * 1000)
        logger.info(
            "task_id=%s target=%s result=%s duration_ms=%s",
            uuid.uuid4().hex[:8],
            target,
            result,
            duration_ms,
        )
