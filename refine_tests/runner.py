from __future__ import annotations

import shlex
import subprocess
import sys
from collections.abc import Sequence

from tests.support import infrastructure


PYTEST_COMMANDS: dict[str, list[str]] = {
    "python": [],
    "pytest": [],
    "cli": ["tests/cli"],
    "smoke-ai": ["tests/smoke_ai_provider_contract"],
    "smoke_ai": ["tests/smoke_ai_provider_contract"],
}


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return run_all([])

    command = args.pop(0)
    if args and args[0] == "--":
        args.pop(0)

    if command in ("all", "full"):
        return run_all(args)
    if command == "setup":
        infrastructure.setup()
        print(f"Refine test infrastructure ready at {infrastructure.base_url()}")
        return 0
    if command == "teardown":
        infrastructure.teardown()
        print("Refine test infrastructure removed")
        return 0
    if command in ("ui", "playwright"):
        return run(["npx", "playwright", "test", *args])
    if command in PYTEST_COMMANDS:
        return run([sys.executable, "-m", "pytest", *PYTEST_COMMANDS[command], *args])
    if command in ("help", "-h", "--help"):
        print_help()
        return 0

    print(f"Unknown test command: {command}", file=sys.stderr)
    print_help(file=sys.stderr)
    return 2


def run_all(args: list[str]) -> int:
    ui_status = run(["npx", "playwright", "test", *args])
    if ui_status != 0:
        return ui_status
    return run([sys.executable, "-m", "pytest", *args])


def run(command: list[str]) -> int:
    print(f"+ {shlex.join(command)}", flush=True)
    return subprocess.call(command)


def print_help(file=sys.stdout) -> None:
    print(
        "\n".join(
            [
                "Usage: uv run test [command] [-- extra args]",
                "",
                "Commands:",
                "  all        Run UI and Python tests (default).",
                "  setup      Create test-app, attach Refine, start UI, and configure smoke-ai.",
                "  teardown   Stop Refine, purge test state, and remove test-app.",
                "  ui         Run Playwright UI tests.",
                "  python     Run all pytest tests.",
                "  cli        Run CLI pytest tests.",
                "  smoke-ai   Run deterministic smoke-ai pytest tests.",
            ]
        ),
        file=file,
    )
