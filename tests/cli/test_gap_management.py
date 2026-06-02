"""CLI smoke tests for Gap management and workflow (smoke-test.md 6, 27-33, 49).

Exercises the `gaps` command group as a user would: create, inspect, update,
move through user-allowed workflow states, revise feedback, bulk-edit, read
logs, and delete — all against the disposable test-app, cleaning up each Gap.
"""

from __future__ import annotations

import pytest

from tests.support.cli import (
    combined_output,
    create_gap_cli,
    delete_gap_cli,
    ensure_reporter,
    gap_field_cli,
    parse_json_stdout,
    run_refine_cli,
)


pytestmark = pytest.mark.refine_cli


@pytest.fixture(scope="module", autouse=True)
def _paused_agents():
    """Pause agent scheduling so user-driven workflow states are deterministic.

    With agents running, moving a Gap to `todo` is immediately picked up by the
    runner and advanced to `in-progress`; pausing keeps the Gap in the state the
    test set so the transition under test is the one observed.
    """
    run_refine_cli("processes", "agents", "--paused")
    try:
        yield
    finally:
        run_refine_cli("processes", "agents", "--running")


def test_gap_create_get_update_delete() -> None:
    """6 + 29 + 31 + 33. Create, inspect, rename/reprioritize, and delete a Gap."""
    gap_id = create_gap_cli(actual="create actual", target="create target")
    try:
        assert gap_field_cli(gap_id, "status") == "backlog"

        updated = run_refine_cli(
            "gaps", "update", gap_id, "--name", "cli renamed", "--priority", "high"
        )
        assert updated.returncode == 0, combined_output(updated)
        assert gap_field_cli(gap_id, "name") == "cli renamed"
        assert gap_field_cli(gap_id, "priority") == "high"
    finally:
        delete_gap_cli(gap_id)

    after = run_refine_cli("gaps", "get", gap_id)
    assert "not found" in combined_output(after).lower()


def test_gap_workflow_transitions() -> None:
    """7 + 28 + 32. Move a Gap through user-allowed workflow states."""
    gap_id = create_gap_cli(actual="wf actual", target="wf target")
    try:
        moved = run_refine_cli("gaps", "update", gap_id, "--status", "todo")
        assert moved.returncode == 0, combined_output(moved)
        assert gap_field_cli(gap_id, "status") == "todo"

        cancelled = run_refine_cli("gaps", "cancel", gap_id)
        assert cancelled.returncode == 0, combined_output(cancelled)
        assert gap_field_cli(gap_id, "status") == "cancelled"

        # Retry reopens a terminal Gap back into the active queue.
        retried = run_refine_cli("gaps", "retry", gap_id)
        assert retried.returncode == 0, combined_output(retried)
        assert gap_field_cli(gap_id, "status") == "todo"
    finally:
        delete_gap_cli(gap_id)


def test_gap_revise_latest_round() -> None:
    """30. Revise the latest feedback round on a Gap."""
    gap_id = create_gap_cli(actual="round actual", target="round target")
    try:
        run_refine_cli("gaps", "update", gap_id, "--status", "todo")
        edited = run_refine_cli(
            "gaps", "edit-round", gap_id,
            "--reporter", "refine-smoke",
            "--actual", "revised actual",
            "--target", "revised target",
        )
        assert edited.returncode == 0, combined_output(edited)

        rounds = gap_field_cli(gap_id, "rounds")
        assert isinstance(rounds, list) and rounds
        assert rounds[-1]["actual"] == "revised actual"
    finally:
        delete_gap_cli(gap_id)


def test_gap_bulk_update_and_delete() -> None:
    """27. Bulk-edit then bulk-delete selected Gaps."""
    ensure_reporter()
    first = create_gap_cli(actual="bulk a1", target="bulk t1")
    second = create_gap_cli(actual="bulk a2", target="bulk t2")
    ids = f"{first},{second}"
    deleted = False
    try:
        bulk = run_refine_cli(
            "gaps", "bulk-update", "--status-update", "todo", "--selected-ids", ids
        )
        assert bulk.returncode == 0, combined_output(bulk)
        assert parse_json_stdout(bulk).get("updated") == 2
        assert gap_field_cli(first, "status") == "todo"
        assert gap_field_cli(second, "status") == "todo"

        removed = run_refine_cli("gaps", "bulk-delete", "--selected-ids", ids)
        assert removed.returncode == 0, combined_output(removed)
        deleted = True
        assert parse_json_stdout(removed).get("deleted") == 2
    finally:
        if not deleted:
            delete_gap_cli(first)
            delete_gap_cli(second)


def test_gap_logs_are_listable() -> None:
    """49. Open logs for a specific Gap."""
    gap_id = create_gap_cli(actual="logs actual", target="logs target")
    try:
        result = run_refine_cli("gaps", "logs", gap_id)
        assert result.returncode == 0, combined_output(result)
        payload = parse_json_stdout(result)
        assert isinstance(payload, dict)
        assert isinstance(payload.get("logs"), list)
    finally:
        delete_gap_cli(gap_id)
