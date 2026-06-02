from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tests.support.infrastructure import port, refine_path, subprocess_env


def run_refine_cli(*args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    cwd = refine_path()
    return subprocess.run(
        ["uv", "run", "refine", *args],
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


def smoke_ai_script() -> Path:
    return Path(__file__).resolve().parents[1] / "smoke_ai_provider_executable"
