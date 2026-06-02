"""CLI smoke tests for the "Multi-Node And Cluster" journeys
(smoke-test.md 67-75) that have a command-line surface.

Covered here: node list/create/activate/transfer/archive, cluster registry
listing, and project-state migration status/run. Remote cluster operations
(register/bootstrap/run) require a reachable SSH host, so they are verified at
the command-surface level. Copying node settings (68) and Git state sync (73)
are driven through the UI/API and are covered by the Playwright specs.
"""

from __future__ import annotations

import pytest

from tests.support.cli import (
    combined_output,
    parse_json_stdout,
    run_refine_cli,
)


pytestmark = pytest.mark.refine_cli

PROBE_NODE_NAME = "refine-smoke-cli-node"


def test_node_list_reports_active_node() -> None:
    """67. The node registry reports the nodes and the active node."""
    result = run_refine_cli("node", "list")
    assert result.returncode == 0, combined_output(result)
    data = parse_json_stdout(result)
    assert isinstance(data, dict), data
    nodes = data.get("nodes")
    assert isinstance(nodes, list) and nodes, f"expected at least one node: {data}"
    assert data.get("active_node_id"), f"expected an active node id: {data}"
    ids = {node.get("id") for node in nodes}
    assert data["active_node_id"] in ids


def test_node_create_activate_transfer_archive_lifecycle() -> None:
    """67 + 69. Create and activate a node, transfer work, then retire it."""
    created = run_refine_cli("node", "create", PROBE_NODE_NAME, timeout=60)
    assert created.returncode == 0, combined_output(created)
    node = parse_json_stdout(created)["node"]
    node_id = node["id"]
    assert node_id, node
    assert node["archived"] is False

    try:
        listed = parse_json_stdout(run_refine_cli("node", "list"))
        ids = {n["id"] for n in listed["nodes"]}
        assert node_id in ids

        activated = run_refine_cli("node", "activate", node_id, timeout=60)
        assert activated.returncode == 0, combined_output(activated)
        after_activate = parse_json_stdout(run_refine_cli("node", "list"))
        assert after_activate["active_node_id"] == node_id

        # No Gaps exist on the disposable app, so the transfer is a clean no-op.
        transfer = run_refine_cli(
            "node", "transfer-gaps", node_id, "--source", "default", timeout=60
        )
        assert transfer.returncode == 0, combined_output(transfer)
        transferred = parse_json_stdout(transfer)
        assert transferred.get("updated") == 0
    finally:
        run_refine_cli("node", "activate", "default", timeout=60)
        run_refine_cli("node", "archive", node_id, timeout=60)

    archived = parse_json_stdout(run_refine_cli("node", "list"))
    by_id = {n["id"]: n for n in archived["nodes"]}
    assert by_id[node_id]["archived"] is True
    assert archived["active_node_id"] == "default"


def test_cluster_list_returns_registry() -> None:
    """70. The cluster registry is listable (empty on a fresh checkout)."""
    result = run_refine_cli("cluster", "list")
    assert result.returncode == 0, combined_output(result)
    data = parse_json_stdout(result)
    assert isinstance(data, dict), data
    assert isinstance(data.get("nodes"), list), data


@pytest.mark.parametrize(
    ("subcommand", "journey"),
    [
        ("register", "71. Register and list cluster nodes"),
        ("bootstrap", "71. Bootstrap a cluster node over SSH"),
        ("run", "72. Run a Refine command on a remote cluster node"),
    ],
)
def test_cluster_remote_subcommand_is_advertised(subcommand: str, journey: str) -> None:
    """Remote cluster operations need a reachable SSH host; verify the surface.

    Executing these would attempt an outbound SSH connection to another machine,
    which is out of scope for a self-contained smoke run. Confirm the subcommand
    is advertised and documents itself.
    """
    listing = run_refine_cli("cluster", "--help")
    assert listing.returncode == 0, combined_output(listing)
    assert subcommand in combined_output(listing).lower(), journey

    help_result = run_refine_cli("cluster", subcommand, "--help")
    assert help_result.returncode == 0, combined_output(help_result)


def test_migrate_status_reports_schema_compatibility() -> None:
    """74. Run project-state migration status."""
    result = run_refine_cli("migrate", "status")
    assert result.returncode == 0, combined_output(result)
    data = parse_json_stdout(result)
    assert isinstance(data, dict), data
    schema = data.get("schema")
    assert isinstance(schema, dict), data
    assert isinstance(schema.get("compatible"), bool), schema


def test_migrate_run_succeeds_when_schema_is_current() -> None:
    """75. Run a required project-state migration (idempotent no-op when current)."""
    status = parse_json_stdout(run_refine_cli("migrate", "status"))
    if status.get("schema", {}).get("migration_required") is True:
        pytest.skip("a migration is genuinely pending; smoke run does not force it")

    result = run_refine_cli("migrate", "run", timeout=90)
    assert result.returncode == 0, combined_output(result)
