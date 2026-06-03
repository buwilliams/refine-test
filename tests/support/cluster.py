"""Stand up several Refine instances that coordinate through a shared git remote.

A real Refine "node" is a separate instance on its own port, attached to its own
clone of a shared repo; instances coordinate by committing `.refine/` state and
pushing/pulling it through a shared remote (in production, GitHub). This module
builds that topology locally and hermetically: a bare git repo plays the role of
the shared remote, and each node is a clone attached on its own port. The git
coordination path (clone, pull-then-push to upstream) is byte-identical to a
GitHub remote, with no network or auth.

Nodes must share one `.refine/` base, or their independent initializations have
no common ancestor and every sync conflicts. So the first node initializes the
base and publishes it; later nodes clone that base and adopt it (attach without
`--force`), exactly as a teammate joins an existing project from its Git URL.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import requests

from tests.support import infrastructure as infra


SEED_FILES = {
    "README.md": (
        "# Refine team smoke target\n\n"
        "Shared target app for the distributed-team smoke test.\n"
    ),
    "app.py": 'def health() -> str:\n    return "ok"\n',
    ".gitignore": "__pycache__/\n*.py[cod]\n",
}


def _git(*args: str, cwd: Path) -> None:
    result = subprocess.run(
        ["git", *args], cwd=cwd, text=True, capture_output=True, timeout=60, check=False
    )
    if result.returncode != 0:
        raise infra.InfrastructureError(
            f"git {' '.join(args)} failed in {cwd}:\n{result.stdout}\n{result.stderr}"
        )


@dataclass
class TeamNode:
    """One Refine instance: a port bound to its own clone of the shared remote."""

    name: str
    port: int
    repo: Path
    node_id: str = ""

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def _env(self) -> dict[str, str]:
        env = infra.subprocess_env()
        # Pin CLI config/app discovery to this node's port-scoped binding.
        env["REFINE_UI_PORT"] = str(self.port)
        return env

    def cli(self, *args: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
        """Run `uv run refine <args>` against this node's port."""
        return subprocess.run(
            ["uv", "run", "refine", *args],
            cwd=infra.refine_path(),
            env=self._env(),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )


def _wait_ready(base_url: str, timeout: float = 45.0) -> None:
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        try:
            response = requests.get(f"{base_url}/api/project/status", timeout=2)
            if response.status_code == 200 and response.json().get("attached") is True:
                return
            last = response.text
        except (requests.RequestException, ValueError) as exc:
            last = str(exc)
        time.sleep(0.5)
    raise infra.InfrastructureError(f"node at {base_url} did not become ready: {last}")


@dataclass
class Cluster:
    """A shared bare remote plus the nodes that have joined it."""

    root: Path
    origin: Path
    nodes: list[TeamNode] = field(default_factory=list)

    def join(self, name: str, port: int, *, initialize: bool, node_name: str) -> TeamNode:
        """Clone the shared remote, attach an instance on `port`, and start it.

        `initialize=True` is the first node: it creates the `.refine/` base
        (attach with --force) and publishes it so later nodes share it.
        `initialize=False` adopts the base already present in the clone (attach
        without --force), the way a teammate joins an existing project.

        A work-owning node named `node_name` is created, activated, and then the
        supervisor is restarted: runtime automation freezes the local node id at
        launch (the worker reads it once and holds it for its lifetime), so a
        node activated after start owns no Gaps until the next launch. The first
        start initializes the database (node create needs the cache tables); the
        restart re-freezes the now-active node. Returns the node with its
        `node_id` populated.
        """
        repo = self.root / f"node-{port}"
        _git("clone", "-q", str(self.origin), str(repo), cwd=self.root)
        _git("config", "user.email", f"{name}@example.invalid", cwd=repo)
        _git("config", "user.name", name, cwd=repo)
        node = TeamNode(name=name, port=port, repo=repo)

        node.cli("stop", str(port), timeout=30)
        target_args = ["target", str(repo), "--port", str(port)]
        if initialize:
            target_args.append("--force")
        attached = node.cli(*target_args, timeout=60)
        if attached.returncode != 0:
            raise infra.InfrastructureError(
                infra._format_cli_failure(f"refine target ({name})", attached)
            )

        started = node.cli("start", str(port), timeout=90)
        if started.returncode != 0:
            raise infra.InfrastructureError(
                infra._format_cli_failure(f"refine start ({name})", started)
            )
        _wait_ready(node.base_url)

        created = node.cli("node", "create", node_name, timeout=60)
        if created.returncode != 0:
            raise infra.InfrastructureError(
                infra._format_cli_failure(f"refine node create ({name})", created)
            )
        node.node_id = _parse_json(created)["node"]["id"]
        activated = node.cli("node", "activate", node.node_id, timeout=60)
        if activated.returncode != 0:
            raise infra.InfrastructureError(
                infra._format_cli_failure(f"refine node activate ({name})", activated)
            )

        restarted = node.cli("restart", str(port), timeout=90)
        if restarted.returncode != 0:
            raise infra.InfrastructureError(
                infra._format_cli_failure(f"refine restart ({name})", restarted)
            )
        _wait_ready(node.base_url)

        resp = requests.patch(
            f"{node.base_url}/api/settings", json={"agent_cli": "smoke-ai"}, timeout=15
        )
        if resp.status_code != 200:
            raise infra.InfrastructureError(
                f"PATCH /api/settings failed for {name}: {resp.status_code} {resp.text}"
            )

        self.nodes.append(node)
        if initialize:
            self.publish(node)
        return node

    def publish(self, node: TeamNode) -> dict:
        """Push `node`'s current `.refine/` state to the shared remote."""
        result = node.cli("app", "sync", "--port", str(node.port), timeout=120)
        payload = _parse_json(result)
        if not payload.get("ok"):
            raise infra.InfrastructureError(
                f"publishing base from {node.name} failed: {payload}"
            )
        return payload


def _parse_json(result: subprocess.CompletedProcess[str]) -> dict:
    import json

    text = result.stdout
    idx = text.find("{")
    if idx == -1:
        raise infra.InfrastructureError(
            f"expected JSON from refine CLI:\n{result.stdout}\n{result.stderr}"
        )
    return json.loads(text[idx:])


@contextmanager
def team_cluster() -> Iterator[Cluster]:
    """Yield a `Cluster` backed by a fresh bare remote seeded with a target app."""
    infra.configure_process_env()
    root = Path(tempfile.mkdtemp(prefix="refine-team-"))
    origin = root / "origin.git"
    cluster = Cluster(root=root, origin=origin)
    try:
        _git("init", "--bare", "-b", "main", str(origin), cwd=root)
        seed = root / "seed"
        seed.mkdir()
        _git("init", "-b", "main", cwd=seed)
        _git("config", "user.email", "seed@example.invalid", cwd=seed)
        _git("config", "user.name", "Refine Seed", cwd=seed)
        for name, body in SEED_FILES.items():
            (seed / name).write_text(body, encoding="utf-8")
        _git("add", "-A", cwd=seed)
        _git("commit", "-q", "-m", "Seed shared target app", cwd=seed)
        _git("remote", "add", "origin", str(origin), cwd=seed)
        _git("push", "-u", "origin", "main", cwd=seed)
        yield cluster
    finally:
        for node in cluster.nodes:
            node.cli("stop", str(node.port), timeout=30)
            node.cli("reset", str(node.port), "--purge", "--yes", timeout=60)
        shutil.rmtree(root, ignore_errors=True)
