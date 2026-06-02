"""CLI smoke tests for reporter management (smoke-test.md 23, 24)."""

from __future__ import annotations

import pytest

from tests.support.cli import (
    combined_output,
    create_gap_cli,
    delete_gap_cli,
    gap_field_cli,
    parse_json_stdout,
    run_refine_cli,
)


pytestmark = pytest.mark.refine_cli


def test_reporter_add_list_delete() -> None:
    """23. Select/manage the reporter for new work."""
    name = "refine-smoke-rep"
    added = run_refine_cli("reporter", "add", name)
    assert added.returncode == 0, combined_output(added)
    reporter_id = parse_json_stdout(added)["reporter"]["id"]

    deleted = False
    try:
        listing = parse_json_stdout(run_refine_cli("reporter", "list"))
        names = [r["name"] for r in listing["reporters"]]
        assert name in names

        removed = run_refine_cli("reporter", "delete", str(reporter_id))
        assert removed.returncode == 0, combined_output(removed)
        deleted = True
        after = parse_json_stdout(run_refine_cli("reporter", "list"))
        assert name not in [r["name"] for r in after["reporters"]]
    finally:
        if not deleted:
            run_refine_cli("reporter", "delete", str(reporter_id))


def test_reporter_rename_cascades_to_gap_attribution() -> None:
    """24. Manage reporters without losing historical Gap attribution."""
    name = "refine-smoke-cascade"
    reporter_id = parse_json_stdout(run_refine_cli("reporter", "add", name))["reporter"]["id"]
    gap_id = create_gap_cli(reporter=name, actual="cascade actual", target="cascade target")
    renamed = f"{name}-renamed"
    try:
        result = run_refine_cli("reporter", "rename", str(reporter_id), renamed, with_port=True)
        assert result.returncode == 0, combined_output(result)

        rounds = gap_field_cli(gap_id, "rounds")
        assert isinstance(rounds, list) and rounds
        assert rounds[0]["reporter"] == renamed
    finally:
        delete_gap_cli(gap_id)
        run_refine_cli("reporter", "delete", str(reporter_id))
