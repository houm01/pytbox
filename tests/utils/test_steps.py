#!/usr/bin/env python3

import pytest

from pytbox.utils.steps import run_step


class DummyLogger:
    """Simple logger spy for step tests."""

    def __init__(self) -> None:
        """Initialize call stores."""
        self.info_calls: list[str] = []
        self.exception_calls: list[str] = []

    def info(self, message: str) -> None:
        """Store info log message."""
        self.info_calls.append(message)

    def exception(self, message: str) -> None:
        """Store exception log message."""
        self.exception_calls.append(message)


def test_run_step_success() -> None:
    """`run_step` should return function result and log success."""
    logger = DummyLogger()
    result = run_step(logger, "sum", lambda left, right: left + right, 1, 2)

    assert result == 3
    assert any("-> sum" in message for message in logger.info_calls)
    assert any("<- sum ok" in message for message in logger.info_calls)


def test_run_step_failure_reraises_original_exception() -> None:
    """`run_step` should log failure and re-raise original error."""
    logger = DummyLogger()

    def _raise_error() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        run_step(logger, "explode", _raise_error)

    assert len(logger.exception_calls) == 1
    assert "failed cost=" in logger.exception_calls[0]
