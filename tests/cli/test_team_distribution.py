"""CLI smoke tests for the "Distributed Team Workflow" journeys
(smoke-test.md 77-83).

This is the team-at-scale flow as a team actually runs it: two Refine instances
on separate ports stand in for two teammates' machines, each a distinct node
attached to its own clone of a shared repo, each with its own reporter. The
instances coordinate by pushing/pulling `.refine/` state through a shared remote
(a local bare repo here; GitHub in production). Work raised on one node
propagates to the other through that remote, with node ownership and reporter
attribution intact.

The single-instance target app the rest of the suite uses has no upstream, so
its state sync silently no-ops; this test deliberately runs against a remote so
the coordination path is genuinely exercised, and asserts the pushes land.

Out of self-contained scope: 83's true concurrent *agent execution* on separate
physical machines. We verify each node owns its own work and that state
propagates between nodes (the property that makes concurrent processing
coherent); driving real agents across hosts belongs to a cluster run.
"""

from __future__ import annotations

import pytest

from tests.support.cli import combined_output, parse_json_stdout
from tests.support.cluster import TeamNode, team_cluster


pytestmark = pytest.mark.refine_cli

# Ports distinct from the suite's session instance (REFINE_BASE_URL, default 8081).
ALICE_PORT = 8082
BOB_PORT = 8083


def _gaps(node: TeamNode, scope: str = "all") -> dict[str, dict]:
    result = node.cli("gaps", "list", "--node", scope, "--limit", "200", "--port", str(node.port))
    assert result.returncode == 0, combined_output(result)
    payload = parse_json_stdout(result)
    return {str(g["id"]): g for g in payload.get("gaps", [])}


def _reporters(node: TeamNode) -> set[str]:
    result = node.cli("reporter", "list")
    assert result.returncode == 0, combined_output(result)
    return {r["name"] for r in parse_json_stdout(result)["reporters"]}


def _node_ids(node: TeamNode) -> set[str]:
    result = node.cli("node", "list")
    assert result.returncode == 0, combined_output(result)
    return {n["id"] for n in parse_json_stdout(result)["nodes"]}


def _gap_field(node: TeamNode, gap_id: str, field: str) -> object:
    result = node.cli("gaps", "get", gap_id)
    assert result.returncode == 0, combined_output(result)
    payload = parse_json_stdout(result)
    gap = payload.get("gap", payload)
    return gap.get(field)


def _create_gap(node: TeamNode, reporter: str, subject: str) -> tuple[str, dict]:
    """Create a Gap on `node`; return its id and the sync result the push produced."""
    result = node.cli(
        "gaps", "create",
        "--reporter", reporter,
        "--actual", f"{subject} is broken",
        "--target", f"{subject} should work",
        "--priority", "low",
        "--port", str(node.port),
    )
    assert result.returncode == 0, combined_output(result)
    payload = parse_json_stdout(result)
    gap = payload.get("gap", payload)
    gap_id = str(gap.get("id") or "")
    assert gap_id, combined_output(result)
    return gap_id, payload.get("sync") or {}


def _assert_pushed(sync: dict, context: str) -> None:
    """The mutation reached the shared remote (not the no-upstream skip path)."""
    assert sync.get("stage") == "synced", f"{context}: expected a pushed sync, got {sync}"
    assert sync.get("pushed_state") is True, f"{context}: expected pushed_state, got {sync}"


def _sync(node: TeamNode) -> dict:
    """Pull the shared remote into `node` and return the sync result."""
    result = node.cli("app", "sync", "--port", str(node.port), timeout=120)
    assert result.returncode == 0, combined_output(result)
    payload = parse_json_stdout(result)
    assert payload.get("ok") is True, payload
    return payload


def test_team_distribution_propagates_through_shared_remote() -> None:
    """77-83. Two nodes raise work and it propagates through the shared remote.

    alice-box and bob-box are separate instances, each its own node with its own
    reporter, attached to clones of one shared repo. A Gap raised on either node
    reaches the other after a sync, owned by the originating node and attributed
    to the originating reporter.
    """
    with team_cluster() as cluster:
        # 77-78. alice's instance (port) initializes the shared .refine/ base as
        # its own node; bob's instance clones and adopts that base as a distinct
        # node, the way a teammate joins the project from its Git URL.
        alice = cluster.join("alice-box", ALICE_PORT, initialize=True, node_name="alice-node")
        bob = cluster.join("bob-box", BOB_PORT, initialize=False, node_name="bob-node")
        node_a, node_b = alice.node_id, bob.node_id

        # 79. Each node manages its own reporters (reporters are per-node).
        added = alice.cli("reporter", "add", "alice")
        assert added.returncode == 0, combined_output(added)
        assert "alice" in _reporters(alice)

        # 80. alice raises work; the create pushes it to the shared remote.
        gap_a, sync_a = _create_gap(alice, "alice", "login redirect")
        _assert_pushed(sync_a, "alice gap create")

        # Until bob pulls, the work is not yet on his node.
        assert gap_a not in _gaps(bob)

        # 81. bob pulls the remote and converges on alice's node and Gap.
        _sync(bob)
        bob_view = _gaps(bob)
        assert gap_a in bob_view, "alice's Gap did not propagate to bob"
        # 82. Node ownership and reporter attribution survive the hop through the remote.
        assert bob_view[gap_a]["node_id"] == node_a, "Gap lost its owning node in transit"
        assert node_a in _node_ids(bob), "alice's node did not propagate"
        rounds = _gap_field(bob, gap_a, "rounds")
        assert isinstance(rounds, list) and rounds and rounds[0]["reporter"] == "alice"

        # bob raises his own work as his own node/reporter, then pushes.
        added = bob.cli("reporter", "add", "bob")
        assert added.returncode == 0, combined_output(added)
        assert "bob" in _reporters(bob)
        gap_b, sync_b = _create_gap(bob, "bob", "billing webhook")
        _assert_pushed(sync_b, "bob gap create")

        # 81-82. alice pulls and converges on bob's node and Gap — coordination
        # flows both directions through the remote, ownership and attribution intact.
        _sync(alice)
        alice_view = _gaps(alice)
        assert gap_b in alice_view, "bob's Gap did not propagate to alice"
        assert alice_view[gap_b]["node_id"] == node_b
        assert node_b in _node_ids(alice)
        assert _gap_field(alice, gap_b, "rounds")[0]["reporter"] == "bob"

        # 83. Both nodes now agree on the full, two-node aggregate backlog.
        assert {gap_a, gap_b} <= set(_gaps(alice))
        assert {gap_a, gap_b} <= set(_gaps(bob))
