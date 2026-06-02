from __future__ import annotations

import subprocess
from pathlib import Path

from tests.support.infrastructure import refine_path, subprocess_env


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


def smoke_ai_script() -> Path:
    return Path(__file__).resolve().parents[1] / "smoke_ai_provider_executable"
