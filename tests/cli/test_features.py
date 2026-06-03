"""CLI smoke tests for the "Feature Organization" journeys (smoke-test.md 84-94).

A Feature is an ordered collection of Gaps for planning larger work. These tests
exercise the CLI surface of the shared Feature operations: create, assign/order,
reorder, remove, derived status/progress, list/search, update, Feature-backed
import, and cascade cancel/delete. All run against the suite's single session
instance, where every record is owned by the active node, so mutations are
permitted.

Out of CLI-smoke scope: Plan Mode defaulting to a Feature (92, chat/UI), live
scheduler serialization within a Feature and parallelism across Features (95,
needs running agents), and cross-node Feature ownership enforcement (needs a
multi-node cluster). The general node-ownership guard is covered elsewhere.
"""

from __future__ import annotations

import json

import pytest

from tests.support.cli import (
    SMOKE_REPORTER,
    combined_output,
    create_gap_cli,
    delete_gap_cli,
    ensure_reporter,
    gap_field_cli,
    parse_json_stdout,
    run_refine_cli,
)


pytestmark = pytest.mark.refine_cli


def _gap(subject: str) -> str:
    """Create a standalone Gap whose text is distinct enough to dodge dedup."""
    return create_gap_cli(actual=f"{subject} is broken", target=f"{subject} should work")


def _create_feature(name: str, description: str | None = None) -> str:
    args = ["features", "create", "--name", name]
    if description is not None:
        args += ["--description", description]
    result = run_refine_cli(*args, with_port=True)
    assert result.returncode == 0, combined_output(result)
    return str(parse_json_stdout(result)["feature"]["id"])


def _show(feature_id: str) -> dict:
    result = run_refine_cli("features", "show", feature_id, with_port=True)
    assert result.returncode == 0, combined_output(result)
    return parse_json_stdout(result)["feature"]


def _ordered_gap_ids(feature: dict) -> list[str]:
    return [str(g["id"]) for g in feature.get("gaps", [])]


def _add_gap(feature_id: str, gap_id: str) -> None:
    result = run_refine_cli("features", "add-gap", feature_id, gap_id, with_port=True)
    assert result.returncode == 0, combined_output(result)


def _delete_feature(feature_id: str) -> None:
    run_refine_cli("features", "delete", feature_id, "--yes", with_port=True)


def test_feature_assign_order_reorder_remove() -> None:
    """84-88. Build a Feature from ordered Gaps, reorder, and remove one."""
    ensure_reporter()
    feature_id = _create_feature("refine-smoke-feature", "planning context")
    g1 = _gap("checkout flow redesign")
    g2 = _gap("audit log viewer")
    g3 = _gap("rate limiter tuning")
    standalone: list[str] = []
    try:
        # 85. Assign existing Gaps; they take the appended Feature order.
        for gap_id in (g1, g2, g3):
            _add_gap(feature_id, gap_id)
        feature = _show(feature_id)
        assert _ordered_gap_ids(feature) == [g1, g2, g3], feature

        # 88. Derived status/progress roll up from the Gaps.
        assert feature["gap_count"] == 3
        assert feature["done_count"] == 0
        assert feature["next_gap"] and str(feature["next_gap"]["id"]) == g1
        # The Gap now carries its Feature association.
        assert str(gap_field_cli(g1, "feature_id") or "").upper() == feature_id.upper()

        # 86. Reorder g1 after g3 -> [g2, g3, g1].
        reordered = run_refine_cli(
            "features", "reorder", feature_id, g1, "--after", g3, with_port=True
        )
        assert reordered.returncode == 0, combined_output(reordered)
        assert _ordered_gap_ids(parse_json_stdout(reordered)["feature"]) == [g2, g3, g1]

        # 87. Remove g2 from the Feature; it becomes standalone but still exists.
        removed = run_refine_cli("features", "remove-gap", feature_id, g2, with_port=True)
        assert removed.returncode == 0, combined_output(removed)
        feature = _show(feature_id)
        assert g2 not in _ordered_gap_ids(feature)
        assert feature["gap_count"] == 2
        assert not (gap_field_cli(g2, "feature_id") or ""), "removed Gap should be standalone"
        standalone.append(g2)
    finally:
        _delete_feature(feature_id)  # cascades the Gaps still associated (g1, g3)
        for gap_id in standalone:
            delete_gap_cli(gap_id)


def test_feature_list_search_and_update() -> None:
    """89-90. Features are listable/searchable, and metadata is editable."""
    feature_id = _create_feature("refine-smoke-listme", "first description")
    try:
        listed = run_refine_cli("features", "list", "--q", "refine-smoke-listme", with_port=True)
        assert listed.returncode == 0, combined_output(listed)
        features = parse_json_stdout(listed)["features"]
        assert any(str(f["id"]) == feature_id for f in features), features

        updated = run_refine_cli(
            "features", "update", feature_id,
            "--name", "refine-smoke-renamed",
            "--description", "second description",
            with_port=True,
        )
        assert updated.returncode == 0, combined_output(updated)
        feature = _show(feature_id)
        assert feature["name"] == "refine-smoke-renamed"
        assert feature["description"] == "second description"
    finally:
        _delete_feature(feature_id)


def test_feature_backed_import_creates_and_appends() -> None:
    """91. Import a batch as a new Feature, then append more to it."""
    ensure_reporter()

    def _drafts(subjects: list[str]) -> str:
        return json.dumps({
            "drafts": [
                {
                    "actual": f"{s} is broken",
                    "target": f"{s} should work",
                    "reporter": SMOKE_REPORTER,
                    "priority": "low",
                }
                for s in subjects
            ]
        })

    created = run_refine_cli(
        "import", "persist",
        _drafts(["webhook retry backoff", "graphql pagination", "session timeout banner"]),
        "--new-feature-name", "refine-smoke-import-feature",
        with_port=True,
    )
    assert created.returncode == 0, combined_output(created)
    payload = parse_json_stdout(created)
    feature_id = payload.get("feature_id")
    assert feature_id, payload
    assert payload["count"] == 3
    try:
        feature = _show(feature_id)
        assert feature["gap_count"] == 3
        assert len(_ordered_gap_ids(feature)) == 3

        appended = run_refine_cli(
            "import", "persist", _drafts(["avatar crop tool", "csv column mapping"]),
            "--feature", feature_id,
            with_port=True,
        )
        assert appended.returncode == 0, combined_output(appended)
        assert parse_json_stdout(appended)["count"] == 2
        assert _show(feature_id)["gap_count"] == 5
    finally:
        _delete_feature(feature_id)


def test_feature_cancel_cascades_to_gaps() -> None:
    """93. Cancelling a Feature cancels its non-terminal Gaps."""
    ensure_reporter()
    feature_id = _create_feature("refine-smoke-cancel")
    g1 = _gap("dark theme support")
    g2 = _gap("saml login support")
    try:
        _add_gap(feature_id, g1)
        _add_gap(feature_id, g2)
        cancelled = run_refine_cli("features", "cancel", feature_id, with_port=True)
        assert cancelled.returncode == 0, combined_output(cancelled)
        assert parse_json_stdout(cancelled)["cancelled"] == 2

        assert gap_field_cli(g1, "status") == "cancelled"
        assert gap_field_cli(g2, "status") == "cancelled"
        assert _show(feature_id)["status"] == "cancelled"
    finally:
        _delete_feature(feature_id)


def test_feature_delete_cascades_to_gaps() -> None:
    """94. Deleting a Feature requires confirmation and removes its Gaps."""
    ensure_reporter()
    feature_id = _create_feature("refine-smoke-delete")
    gap_id = _gap("email digest scheduling")
    _add_gap(feature_id, gap_id)

    # Cascade delete is guarded behind --yes.
    refused = run_refine_cli("features", "delete", feature_id, with_port=True)
    assert refused.returncode != 0, combined_output(refused)
    assert _show(feature_id)["gap_count"] == 1

    deleted = run_refine_cli("features", "delete", feature_id, "--yes", with_port=True)
    assert deleted.returncode == 0, combined_output(deleted)
    assert parse_json_stdout(deleted).get("deleted") is True

    # The Feature is gone and its Gap was cascade-deleted.
    assert run_refine_cli("features", "show", feature_id, with_port=True).returncode != 0
    assert run_refine_cli("gaps", "get", gap_id).returncode != 0
