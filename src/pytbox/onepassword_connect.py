#!/usr/bin/env python3
"""1Password Connect client wrapper with retry and idempotency safeguards."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

from onepasswordconnectsdk.client import new_client_from_environment
from onepasswordconnectsdk.models import Field, Item

T = TypeVar("T")


class OnePasswordConnect:
    """Sync wrapper for common 1Password Connect item operations."""

    def __init__(
        self,
        vault_id: str,
        request_timeout: float = 5.0,
        max_retries: int = 3,
        retry_backoff_base: float = 0.5,
        idempotency_ttl_seconds: int = 300,
    ) -> None:
        """Initialize client wrapper.

        Args:
            vault_id: Target vault ID for all operations.
            request_timeout: HTTP request timeout in seconds.
            max_retries: Max retry attempts. Value is capped to 3.
            retry_backoff_base: Base seconds for exponential backoff.
            idempotency_ttl_seconds: In-memory idempotency TTL for writes.
        """
        self.client = new_client_from_environment()
        self.vault_id = vault_id
        self.request_timeout = request_timeout
        self.max_retries = max(1, min(max_retries, 3))
        self.retry_backoff_base = retry_backoff_base
        self.idempotency_ttl_seconds = idempotency_ttl_seconds
        self._idempotency_cache: Dict[str, Tuple[float, Any]] = {}
        self.logger = logging.getLogger(__name__)
        self._configure_timeout()

    def create_item(
        self,
        name: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        notes: str = "create by automation",
        tags: Optional[List[str]] = None,
    ) -> Any:
        """Create a login item in the configured vault.

        Args:
            name: Item title.
            username: Username value.
            password: Password value.
            notes: Note value.
            tags: Optional tag list.

        Returns:
            Any: Created 1Password item object.
        """
        key = self._build_idempotency_key(
            operation="create_item",
            parts=[name, username, password, notes, tags],
        )

        def _caller() -> Any:
            new_item = Item(
                title=name,
                category="LOGIN",
                tags=tags,
                fields=[
                    Field(value=username, purpose="USERNAME"),
                    Field(value=password, purpose="PASSWORD"),
                    Field(value=notes, purpose="NOTES"),
                ],
            )
            return self._execute_with_retry(
                action=lambda: self.client.create_item(self.vault_id, new_item),
                task_id=name or "-",
                target="create_item",
            )

        return self._run_idempotent(key=key, caller=_caller)

    def delete_item(self, item_id: str) -> Any:
        """Delete item by ID.

        Args:
            item_id: Item ID.

        Returns:
            Any: SDK delete response, usually ``None``.
        """
        key = self._build_idempotency_key(operation="delete_item", parts=[item_id])
        return self._run_idempotent(
            key=key,
            caller=lambda: self._execute_with_retry(
                action=lambda: self.client.delete_item(item_id, self.vault_id),
                task_id=item_id,
                target="delete_item",
            ),
        )

    def get_item(self, item_id: str) -> Any:
        """Get item detail by ID.

        Args:
            item_id: Item ID.

        Returns:
            Any: 1Password item object.
        """
        return self._execute_with_retry(
            action=lambda: self.client.get_item(item_id, self.vault_id),
            task_id=item_id,
            target="get_item",
        )

    def get_item_by_title(self, title: str = "", totp: bool = False) -> Any:
        """Get item fields by title or return the first TOTP value.

        Args:
            title: Item title.
            totp: Whether to return TOTP value directly.

        Returns:
            Any: Dict of fields when ``totp=False``; TOTP string or ``None`` when ``totp=True``.
        """
        item = self._execute_with_retry(
            action=lambda: self.client.get_item_by_title(title, self.vault_id),
            task_id=title or "-",
            target="get_item_by_title",
        )

        if totp:
            for field in item.fields:
                if getattr(field, "totp", None) is not None:
                    return field.totp
            return None

        value: Dict[str, Any] = {}
        for field in item.fields:
            label = getattr(field, "label", None) or getattr(field, "purpose", None)
            if label is not None:
                value[label] = getattr(field, "value", None)
        return value

    def update_item(
        self,
        item_id: str,
        name: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> Any:
        """Update an existing item by ID.

        Args:
            item_id: Item ID.
            name: New title when provided.
            username: New username when provided.
            password: New password when provided.
            tags: New tag list. ``[]`` is allowed and means clear tags.
            notes: New notes when provided.

        Returns:
            Any: Updated 1Password item object.
        """
        key = self._build_idempotency_key(
            operation="update_item",
            parts=[item_id, name, username, password, tags, notes],
        )

        def _caller() -> Any:
            update_target = self.get_item(item_id=item_id)

            if name is not None:
                update_target.title = name

            for field in update_target.fields:
                purpose = getattr(field, "purpose", None)
                if purpose == "USERNAME" and username is not None:
                    field.value = username
                if purpose == "PASSWORD" and password is not None:
                    field.value = password
                if purpose == "NOTES" and notes is not None:
                    field.value = notes

            if tags is not None:
                update_target.tags = tags

            return self._execute_with_retry(
                action=lambda: self.client.update_item(item_id, self.vault_id, update_target),
                task_id=item_id,
                target="update_item",
            )

        return self._run_idempotent(key=key, caller=_caller)

    def search_item(self, title: Optional[str] = None, tag: Optional[str] = None) -> list[Any]:
        """Search items by title, tag, or both.

        Args:
            title: Title filter.
            tag: Tag filter.

        Returns:
            list[Any]: Matched item summaries.
        """
        filter_query = self._build_filter_query(title=title, tag=tag)
        return self._execute_with_retry(
            action=lambda: self.client.get_items(self.vault_id, filter_query=filter_query),
            task_id=title or tag or "-",
            target="search_item",
        )

    def _configure_timeout(self) -> None:
        """Apply explicit timeout on SDK HTTP session when available."""
        session = getattr(self.client, "session", None)
        if session is None:
            return
        try:
            session.timeout = self.request_timeout
        except Exception as exc:  # pragma: no cover - defensive; depends on SDK internals.
            self.logger.debug("failed to set timeout: %s", exc.__class__.__name__)

    def _execute_with_retry(
        self,
        action: Callable[[], T],
        task_id: str,
        target: str,
    ) -> T:
        """Execute an external request with bounded retries.

        Args:
            action: Callable that performs the SDK request.
            task_id: Task identifier for operation logs.
            target: Target operation name.

        Returns:
            T: Value returned by ``action``.

        Raises:
            Exception: Re-raises the final request exception after retries.
        """
        for attempt in range(1, self.max_retries + 1):
            started_at = time.monotonic()
            try:
                result = action()
                duration_ms = int((time.monotonic() - started_at) * 1000)
                self._log_step(
                    task_id=task_id,
                    target=target,
                    result=f"success_attempt_{attempt}",
                    duration_ms=duration_ms,
                )
                return result
            except Exception as exc:
                duration_ms = int((time.monotonic() - started_at) * 1000)
                result = f"error_{exc.__class__.__name__}_attempt_{attempt}"
                self._log_step(
                    task_id=task_id,
                    target=target,
                    result=result,
                    duration_ms=duration_ms,
                )
                if attempt >= self.max_retries:
                    raise
                time.sleep(self.retry_backoff_base * (2 ** (attempt - 1)))
        raise RuntimeError("unexpected retry loop exit")

    def _build_filter_query(self, title: Optional[str], tag: Optional[str]) -> Optional[str]:
        """Build item query with optional title/tag filters.

        Args:
            title: Title filter value.
            tag: Tag filter value.

        Returns:
            Optional[str]: SDK filter query string, or ``None`` when no filters are set.
        """
        clauses: List[str] = []
        if title:
            clauses.append(f'title eq "{self._escape_filter_value(title)}"')
        if tag:
            clauses.append(f'tag eq "{self._escape_filter_value(tag)}"')
        if not clauses:
            return None
        return " and ".join(clauses)

    def _escape_filter_value(self, value: str) -> str:
        """Escape filter value for double-quoted query string.

        Args:
            value: Raw filter value.

        Returns:
            str: Escaped value.
        """
        return value.replace('"', '\\"')

    def _build_idempotency_key(self, operation: str, parts: List[Any]) -> Optional[str]:
        """Build idempotency cache key for write operations.

        Args:
            operation: Operation name.
            parts: Value list that identifies a logical write request.

        Returns:
            Optional[str]: Hash key in current TTL window, or ``None`` when disabled.
        """
        if self.idempotency_ttl_seconds <= 0:
            return None
        window = int(time.time() // self.idempotency_ttl_seconds)
        payload = [operation, window, parts]
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _run_idempotent(self, key: Optional[str], caller: Callable[[], T]) -> T:
        """Execute write operation with in-memory idempotency cache.

        Args:
            key: Idempotency key. ``None`` disables cache.
            caller: Callable that performs the write request.

        Returns:
            T: Cached or fresh result.
        """
        if key is None:
            return caller()

        now = time.time()
        self._cleanup_idempotency_cache(now_ts=now)
        cached = self._idempotency_cache.get(key)
        if cached and now - cached[0] <= self.idempotency_ttl_seconds:
            return cached[1]

        result = caller()
        self._idempotency_cache[key] = (now, result)
        return result

    def _cleanup_idempotency_cache(self, now_ts: float) -> None:
        """Remove expired idempotency cache records.

        Args:
            now_ts: Current UNIX timestamp.
        """
        if self.idempotency_ttl_seconds <= 0:
            self._idempotency_cache.clear()
            return
        expired_keys = [
            cache_key
            for cache_key, (created_at, _resp) in self._idempotency_cache.items()
            if now_ts - created_at > self.idempotency_ttl_seconds
        ]
        for cache_key in expired_keys:
            self._idempotency_cache.pop(cache_key, None)

    def _log_step(
        self,
        task_id: str,
        target: str,
        result: str,
        duration_ms: int,
    ) -> None:
        """Write key-step operation log.

        Args:
            task_id: Operation task ID.
            target: Target method or endpoint.
            result: Result summary.
            duration_ms: Cost in milliseconds.
        """
        self.logger.info(
            "[onepassword_connect] task_id=%s target=%s result=%s duration_ms=%s",
            task_id,
            target,
            result,
            duration_ms,
        )


if __name__ == "__main__":
    pass
