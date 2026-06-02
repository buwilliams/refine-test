from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tests.support.infrastructure import port, refine_path, subprocess_env


def run_refine_cli(
    *args: str, timeout: int = 30, with_port: bool = False
) -> subprocess.CompletedProcess[str]:
    """Invoke `uv run refine <args>` from REFINE_PATH.

    Refine CLI commands target the configured port (default 8080) unless a port
    is explicitly passed. The suite runs on a non-default port, so pass
    `with_port=True` for any command that accepts a `--port` option to target the
    running instance explicitly. (Commands without `--port` resolve the
    configured port from `REFINE_UI_PORT`, which the infrastructure exports.)
    """
    cwd = refine_path()
    extra = ["--port", str(port())] if with_port else []
    return subprocess.run(
        ["uv", "run", "refine", *args, *extra],
        cwd=cwd,
        env=subprocess_env(),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return f"{result.stdout}\n{result.stderr}"


def parse_json_stdout(result: subprocess.CompletedProcess[str]) -> object:
    """Parse a CLI command's JSON stdout, tolerating leading non-JSON lines.

    Some commands emit warnings before their JSON payload; find the first line
    that begins a JSON document and parse from there.
    """
    text = result.stdout
    for marker in ("{", "["):
        idx = text.find(marker)
        if idx != -1:
            try:
                return json.loads(text[idx:])
            except json.JSONDecodeError:
                continue
    raise AssertionError(f"stdout was not JSON:\n{combined_output(result)}")


def configured_port() -> str:
    return str(port())


SMOKE_REPORTER = "refine-smoke"


def ensure_reporter(name: str = SMOKE_REPORTER) -> None:
    """Ensure a reporter exists (the CLI's `reporter add` is idempotent)."""
    run_refine_cli("reporter", "add", name)


def create_gap_cli(
    *,
    actual: str = "refine-smoke actual",
    target: str = "refine-smoke target",
    reporter: str = SMOKE_REPORTER,
    priority: str = "low",
) -> str:
    """Create a disposable Gap through the CLI and return its id."""
    ensure_reporter(reporter)
    result = run_refine_cli(
        "gaps", "create",
        "--reporter", reporter,
        "--actual", actual,
        "--target", target,
        "--priority", priority,
        with_port=True,
    )
    payload = parse_json_stdout(result)
    assert isinstance(payload, dict), combined_output(result)
    gap = payload.get("gap", payload)
    gap_id = str(gap.get("id") or "")
    assert gap_id, combined_output(result)
    return gap_id


def gap_field_cli(gap_id: str, field: str) -> object:
    """Read one field off a Gap via `gaps get`."""
    payload = parse_json_stdout(run_refine_cli("gaps", "get", gap_id))
    assert isinstance(payload, dict)
    gap = payload.get("gap", payload)
    return gap.get(field)


def delete_gap_cli(gap_id: str) -> None:
    if gap_id:
        run_refine_cli("gaps", "delete", gap_id, with_port=True)


def smoke_ai_script() -> Path:
    return Path(__file__).resolve().parents[1] / "smoke_ai_provider_executable"
