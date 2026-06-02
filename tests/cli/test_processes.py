"""CLI smoke tests for managed-process control (smoke-test.md 63-65)."""

from __future__ import annotations

import pytest

from tests.support.cli import parse_json_stdout, run_refine_cli


pytestmark = pytest.mark.refine_cli


def test_processes_list_reports_runtime_state() -> None:
    """65. Inspect runner processes and background jobs."""
    payload = parse_json_stdout(run_refine_cli("processes", "list"))
    assert isinstance(payload, dict)
    assert "backend" in payload
    assert isinstance(payload.get("running"), list)


def test_processes_pause_and_unpause_agents() -> None:
    """63. Pause and unpause agent scheduling."""
    try:
        paused = parse_json_stdout(run_refine_cli("processes", "agents", "--paused"))
        assert paused.get("agents_paused") is True
        assert parse_json_stdout(run_refine_cli("processes", "list")).get("agents_paused") is True
    finally:
        resumed = parse_json_stdout(run_refine_cli("processes", "agents", "--running"))
        assert resumed.get("agents_paused") is False


def test_processes_stop_and_start_background() -> None:
    """64. Stop and restart background processes."""
    try:
        stopped = parse_json_stdout(run_refine_cli("processes", "background", "--stopped"))
        assert stopped.get("stopped") is True
    finally:
        started = parse_json_stdout(run_refine_cli("processes", "background", "--running"))
        assert started.get("stopped") is False
