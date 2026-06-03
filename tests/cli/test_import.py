"""CLI smoke tests for importing Gaps (smoke-test.md 25)."""

from __future__ import annotations

import json

import pytest

from tests.support.cli import (
    SMOKE_REPORTER,
    combined_output,
    delete_gap_cli,
    ensure_reporter,
    parse_json_stdout,
    run_refine_cli,
)


pytestmark = pytest.mark.refine_cli

CSV = "\n".join(
    [
        "actual,target,reporter,priority",
        f"Import A,Import B,{SMOKE_REPORTER},low",
        f"Import C,Import D,{SMOKE_REPORTER},medium",
    ]
)


def test_import_parse_csv() -> None:
    """25. Parse pasted CSV into Gap drafts."""
    result = run_refine_cli("import", "parse-csv", CSV)
    assert result.returncode == 0, combined_output(result)
    payload = parse_json_stdout(result)
    assert payload.get("count") == 2
    drafts = payload.get("drafts")
    assert isinstance(drafts, list) and len(drafts) == 2
    assert drafts[0]["actual"] == "Import A"
    assert drafts[1]["priority"] == "medium"


def test_import_persist_creates_gaps() -> None:
    """25. Persist reviewed import drafts as Gaps."""
    ensure_reporter()
    drafts = parse_json_stdout(run_refine_cli("import", "parse-csv", CSV))["drafts"]
    persisted = run_refine_cli("import", "persist", json.dumps({"drafts": drafts}), with_port=True)
    assert persisted.returncode == 0, combined_output(persisted)
    payload = parse_json_stdout(persisted)

    created = payload.get("created") or []
    created_ids = [c if isinstance(c, str) else c.get("id") for c in created]
    try:
        assert payload.get("count") == 2
        assert len([cid for cid in created_ids if cid]) == 2
    finally:
        for gap_id in created_ids:
            delete_gap_cli(gap_id)


# Distinct subjects so cluster-wide dedup does not collapse the batch.
LARGE_SUBJECTS = [
    "login redirect", "billing webhook", "search pagination", "csv export",
    "dark mode toggle", "avatar upload", "tooltip copy", "timezone handling",
]


def test_import_persist_large_inline_json() -> None:
    """25. Persist a large batch passed as inline JSON.

    Regression guard: a batch whose inline JSON exceeds the OS filename limit
    used to crash with `OSError: File name too long`, because the argument was
    probed with `Path.is_file()` before being treated as JSON. Inline JSON over
    ~255 bytes must now parse as JSON rather than be mistaken for a file path.
    """
    ensure_reporter()
    drafts = [
        {
            "actual": f"{subject} is broken",
            "target": f"{subject} should work",
            "reporter": SMOKE_REPORTER,
            "priority": "low",
        }
        for subject in LARGE_SUBJECTS
    ]
    blob = json.dumps({"drafts": drafts})
    assert len(blob) > 255, "inline JSON must exceed the filename limit to exercise the fix"

    persisted = run_refine_cli("import", "persist", blob, with_port=True)
    assert persisted.returncode == 0, combined_output(persisted)
    payload = parse_json_stdout(persisted)

    created = payload.get("created") or []
    created_ids = [c if isinstance(c, str) else c.get("id") for c in created]
    try:
        assert payload.get("count") == len(LARGE_SUBJECTS), payload
        assert len([cid for cid in created_ids if cid]) == len(LARGE_SUBJECTS)
    finally:
        for gap_id in created_ids:
            delete_gap_cli(gap_id)
