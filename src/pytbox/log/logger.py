#!/usr/bin/env python3

"""Application logger wrapper with resilient external sinks."""

from __future__ import annotations

import inspect
import logging
import os
import sys
import time
import traceback
import uuid
from typing import Any, Callable

from loguru import logger

from ..alicloud.sls import AliCloudSls
from ..database.mongo import Mongo
from ..dida365 import Dida365
from ..feishu.client import Client as FeishuClient
from ..schemas.response import ReturnResponse
from ..utils.timeutils import TimeUtils
from .victorialog import Victorialog


logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | <level>{message}</level>"
    ),
)


class AppLogger:
    """Application logger with external sink support."""

    def __init__(
        self,
        app_name: str = "inbox",
        stream: str = "automation",
        enable_victorialog: bool = False,
        victorialog_url: str | None = None,
        mongo: Mongo | None = None,
        feishu: FeishuClient | None = None,
        dida: Dida365 | None = None,
        enable_sls: bool = False,
        sls_access_key_id: str | None = None,
        sls_access_key_secret: str | None = None,
        sls_project: str | None = None,
        sls_logstore: str | None = None,
        sls_topic: str | None = None,
    ) -> None:
        """Initialize AppLogger.

        Args:
            app_name: App name used for alert title and sink fields.
            stream: VictoriaLogs stream field.
            enable_victorialog: Whether to send logs to VictoriaLogs.
            victorialog_url: VictoriaLogs base URL.
            mongo: Mongo client used for deduping alerts.
            feishu: Feishu client used for notifications.
            dida: Dida client used for issue tracking tasks.
            enable_sls: Whether to send logs to AliCloud SLS.
            sls_access_key_id: SLS access key id.
            sls_access_key_secret: SLS access key secret.
            sls_project: SLS project name.
            sls_logstore: SLS logstore name.
            sls_topic: SLS topic, defaults to ``program``.
        """
        self.app_name = app_name
        self.stream = stream
        self.enable_victorialog = enable_victorialog
        self.enable_sls = enable_sls
        self.mongo = mongo
        self.feishu = feishu
        self.dida = dida
        self.sls_topic = sls_topic or "program"
        self._std_logger = logging.getLogger(__name__)

        self.victorialog = Victorialog(url=victorialog_url)
        self.sls = AliCloudSls(
            access_key_id=sls_access_key_id,
            access_key_secret=sls_access_key_secret,
            project=sls_project,
            logstore=sls_logstore,
        )

    def _get_caller_info(self) -> tuple[str, int, str, str]:
        """Get caller info with low-overhead frame traversal.

        Returns:
            tuple[str, int, str, str]: Filename, line number, function name,
            and absolute filename.
        """
        frame = inspect.currentframe()
        caller = frame.f_back.f_back if frame and frame.f_back and frame.f_back.f_back else None
        try:
            if caller is None:
                return "unknown", 0, "unknown", ""
            call_full_filename = caller.f_code.co_filename
            caller_filename = os.path.basename(call_full_filename)
            caller_lineno = caller.f_lineno
            caller_function = caller.f_code.co_name
            return caller_filename, caller_lineno, caller_function, call_full_filename
        finally:
            del frame
            del caller

    def debug(self, message: str) -> None:
        """Record a debug log."""
        self._log_and_ship(level="DEBUG", message=message)

    def info(self, message: str = "", feishu_notify: bool = False) -> None:
        """Record an info log.

        Args:
            message: Log message.
            feishu_notify: Whether to send an immediate Feishu notification.
        """
        caller_filename, caller_lineno, caller_function, call_full_filename = self._log_and_ship(
            level="INFO",
            message=message,
        )

        if not feishu_notify:
            return
        if self.feishu is None:
            logger.warning("feishu notify is skipped because feishu client is missing")
            return

        self._safe_sink_call(
            target="feishu.send_message_notify",
            caller=lambda: self.feishu.extensions.send_message_notify(
                title=f"自动化脚本告警: {self.app_name}",
                content=f"触发时间: {TimeUtils.get_current_time_str()}\n{message}",
            ),
        )

    def warning(self, message: str) -> None:
        """Record a warning log."""
        self._log_and_ship(level="WARN", message=message)

    def error(self, message: str) -> None:
        """Record an error log and trigger deduped notifications."""
        caller_filename, caller_lineno, caller_function, call_full_filename = self._log_and_ship(
            level="ERROR",
            message=message,
        )

        if self.feishu is None:
            return
        if self.mongo is None:
            logger.warning("error notification dedupe is skipped because mongo client is missing")
            return

        should_notify = True
        ok, existing_message = self._run_with_protection(
            target="mongo.find_one",
            caller=lambda: self.mongo.collection.find_one({"message": message}, sort=[("time", -1)]),
        )
        if ok and isinstance(existing_message, dict) and "time" in existing_message:
            current_time = TimeUtils.get_now_time_mongo()
            ok_diff, diff_hours = self._run_with_protection(
                target="time.get_time_diff_hours",
                caller=lambda: TimeUtils.get_time_diff_hours(existing_message["time"], current_time),
            )
            if ok_diff and isinstance(diff_hours, (int, float)) and diff_hours <= 36:
                should_notify = False

        if not should_notify:
            return

        current_time = TimeUtils.get_now_time_mongo()
        self._safe_sink_call(
            target="mongo.insert_one",
            caller=lambda: self.mongo.collection.insert_one(
                {
                    "message": message,
                    "time": current_time,
                    "file_name": caller_filename,
                    "line_number": caller_lineno,
                    "function_name": caller_function,
                }
            ),
        )

        content_list = [
            f"{self.feishu.extensions.format_rich_text(text='app:', color='blue', bold=True)} {self.app_name}",
            f"{self.feishu.extensions.format_rich_text(text='message:', color='blue', bold=True)} {message}",
            f"{self.feishu.extensions.format_rich_text(text='file_name:', color='blue', bold=True)} {caller_filename}",
            f"{self.feishu.extensions.format_rich_text(text='line_number:', color='blue', bold=True)} {caller_lineno}",
            f"{self.feishu.extensions.format_rich_text(text='function_name:', color='blue', bold=True)} {caller_function}",
        ]
        self._safe_sink_call(
            target="feishu.send_message_notify",
            caller=lambda: self.feishu.extensions.send_message_notify(
                title=f"自动化脚本告警: {self.app_name}",
                content="\n".join(content_list),
            ),
        )

        if self.dida is not None:
            dida_content_list = [
                f"**app**: {self.app_name}",
                f"**message**: {message}",
                f"**file_name**: {caller_filename}",
                f"**line_number**: {caller_lineno}",
                f"**function_name**: {caller_function}",
            ]
            self._safe_sink_call(
                target="dida.task_create",
                caller=lambda: self.dida.task_create(
                    project_id="65e87d2b3e73517c2cdd9d63",
                    title=f"自动化脚本告警: {self.app_name}",
                    content="\n".join(dida_content_list),
                    tags=["L-程序告警", "t-问题处理"],
                ),
            )

    def critical(self, message: str) -> None:
        """Record a critical log."""
        self._log_and_ship(level="CRITICAL", message=message)

    def exception(self, message: str) -> None:
        """Record exception log and traceback details."""
        caller_filename, caller_lineno, caller_function, call_full_filename = self._get_caller_info()
        logger.exception(f"[{caller_filename}:{caller_lineno}:{caller_function}] {message}")
        traceback_content = traceback.format_exc()
        self._emit_external_logs(
            level="EXCEPTION",
            message=f"{message}\n{traceback_content}",
            caller_filename=caller_filename,
            caller_lineno=caller_lineno,
            caller_function=caller_function,
            call_full_filename=call_full_filename,
        )

    def _log_and_ship(self, level: str, message: str) -> tuple[str, int, str, str]:
        """Log locally and forward to external sinks.

        Args:
            level: Log level.
            message: Log message.

        Returns:
            tuple[str, int, str, str]: Caller metadata tuple.
        """
        caller_filename, caller_lineno, caller_function, call_full_filename = self._get_caller_info()
        log_method = getattr(logger, level.lower() if level != "WARN" else "warning")
        log_method(f"[{caller_filename}:{caller_lineno}:{caller_function}] {message}")
        self._emit_external_logs(
            level=level,
            message=message,
            caller_filename=caller_filename,
            caller_lineno=caller_lineno,
            caller_function=caller_function,
            call_full_filename=call_full_filename,
        )
        return caller_filename, caller_lineno, caller_function, call_full_filename

    def _emit_external_logs(
        self,
        level: str,
        message: str,
        caller_filename: str,
        caller_lineno: int,
        caller_function: str,
        call_full_filename: str,
    ) -> None:
        """Emit logs to external sinks with isolation.

        Args:
            level: Log level.
            message: Log message.
            caller_filename: Caller short filename.
            caller_lineno: Caller line number.
            caller_function: Caller function name.
            call_full_filename: Caller full filename.
        """
        if self.enable_victorialog:
            self._safe_sink_call(
                target="victorialog.send_program_log",
                caller=lambda: self.victorialog.send_program_log(
                    stream=self.stream,
                    level=level,
                    message=message,
                    app_name=self.app_name,
                    file_name=call_full_filename,
                    line_number=caller_lineno,
                    function_name=caller_function,
                ),
            )
        if self.enable_sls:
            self._safe_sink_call(
                target="sls.put_logs",
                caller=lambda: self.sls.put_logs(
                    topic=self.sls_topic,
                    level=level,
                    msg=message,
                    app=self.app_name,
                    caller_filename=caller_filename,
                    caller_lineno=caller_lineno,
                    caller_function=caller_function,
                    call_full_filename=call_full_filename,
                ),
            )

    def _safe_sink_call(self, target: str, caller: Callable[[], Any]) -> Any | None:
        """Execute sink call and suppress failures.

        Args:
            target: Sink target name for step logs.
            caller: Callable to execute.

        Returns:
            Any | None: Callable return value when successful.
        """
        ok, value = self._run_with_protection(target=target, caller=caller)
        if ok:
            return value
        return None

    def _run_with_protection(self, target: str, caller: Callable[[], Any]) -> tuple[bool, Any]:
        """Run callable with failure isolation and key-step logging.

        Args:
            target: External target identifier.
            caller: Callable to execute.

        Returns:
            tuple[bool, Any]: Success flag and callable result.
        """
        task_id = uuid.uuid4().hex[:8]
        started_at = time.monotonic()
        try:
            value = caller()
            duration_ms = int((time.monotonic() - started_at) * 1000)
            result = "ok"
            if isinstance(value, ReturnResponse):
                result = "ok" if value.code == 0 else f"fail_code_{value.code}"
            self._log_step(task_id=task_id, target=target, result=result, duration_ms=duration_ms)
            return True, value
        except Exception as exc:
            duration_ms = int((time.monotonic() - started_at) * 1000)
            self._log_step(task_id=task_id, target=target, result="exception", duration_ms=duration_ms)
            logger.warning(f"sink call failed target={target} error={exc}")
            return False, None

    def _log_step(self, task_id: str, target: str, result: str, duration_ms: int) -> None:
        """Write key-step reliability log.

        Args:
            task_id: Correlation id.
            target: Target operation.
            result: Result summary.
            duration_ms: Duration in milliseconds.
        """
        self._std_logger.info(
            "[app_logger] task_id=%s target=%s result=%s duration_ms=%s",
            task_id,
            target,
            result,
            duration_ms,
        )


if __name__ == "__main__":
    pass
