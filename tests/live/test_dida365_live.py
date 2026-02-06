#!/usr/bin/env python3

from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest

from pytbox.dida365 import Dida365

pytestmark = pytest.mark.live


def _need(name: str) -> str:
    value = os.getenv(name)
    if not value:
        pytest.skip(f"missing env: {name}")
    return value


@pytest.fixture
def dida() -> Dida365:
    return Dida365(
        access_token=_need("DIDA_ACCESS_TOKEN"),
        cookie=_need("DIDA_COOKIE"),
        timeout=5,
        max_retries=3,
        retry_backoff_base=0.5,
    )

def test_live_get_projects(dida: Dida365) -> None:
    result = dida.get_projects()
    assert result.code == 0
    assert isinstance(result.data, list)


def test_live_task_list_readonly(dida: Dida365) -> None:
    project_id = _need("DIDA_PROJECT_ID")
    tasks = list(dida.task_list(project_id=project_id, enhancement=True))
    assert isinstance(tasks, list)


def test_live_task_write_flow(dida: Dida365) -> None:
    if os.getenv("DIDA_LIVE_ALLOW_WRITE") != "1":
        pytest.skip("set DIDA_LIVE_ALLOW_WRITE=1 to enable write test")

    project_id = _need("DIDA_PROJECT_ID")
    title = f"[live] pytbox {datetime.utcnow().isoformat()}"

    create_result = dida.task_create(
        project_id=project_id,
        title=title,
        content="live smoke test",
        start_date=datetime.utcnow() + timedelta(minutes=1),
    )
    assert create_result.code == 0
    assert isinstance(create_result.data, dict)
    task_id = create_result.data.get("id")
    assert task_id

    update_result = dida.task_update(
        project_id=project_id,
        task_id=task_id,
        content="updated by live test",
    )
    assert update_result.code == 0

    complete_result = dida.task_complete(project_id=project_id, task_id=task_id)
    assert complete_result.code == 0
