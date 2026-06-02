"""CLI smoke tests for chat sessions (smoke-test.md 34)."""

from __future__ import annotations

import pytest

from tests.support.cli import (
    combined_output,
    create_gap_cli,
    delete_gap_cli,
    parse_json_stdout,
    run_refine_cli,
)


pytestmark = pytest.mark.refine_cli


def test_chat_start_read_stop_with_gap_context() -> None:
    """34. Open chat with the agent using Gap context."""
    gap_id = create_gap_cli(actual="chat actual", target="chat target")
    session_id = ""
    try:
        started = run_refine_cli("chat", "start", "--gap-id", gap_id, with_port=True)
        assert started.returncode == 0, combined_output(started)
        session_id = str(parse_json_stdout(started).get("session_id") or "")
        assert session_id

        read = run_refine_cli("chat", "read", session_id, with_port=True)
        assert read.returncode == 0, combined_output(read)
        assert isinstance(parse_json_stdout(read), dict)
    finally:
        if session_id:
            run_refine_cli("chat", "stop", session_id, with_port=True)
        delete_gap_cli(gap_id)
