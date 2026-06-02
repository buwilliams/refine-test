from __future__ import annotations

import pytest

from tests.support.cli import run_refine_cli
from tests.support.env import TEST_APP_PATH


pytestmark = pytest.mark.refine_cli


def _combined_output(result) -> str:
    return f"{result.stdout}\n{result.stderr}"


def test_cli_help_runs_from_refine_path() -> None:
    result = run_refine_cli("--help")
    assert result.returncode == 0, _combined_output(result)
    assert "refine" in _combined_output(result).lower()


def test_cli_read_only_status_or_config_command_runs() -> None:
    help_result = run_refine_cli("--help")
    assert help_result.returncode == 0, _combined_output(help_result)
    help_text = _combined_output(help_result).lower()

    candidates = [
        ("status",),
        ("config",),
        ("settings",),
        ("doctor",),
    ]
    available = [command for command in candidates if command[0] in help_text]
    if not available:
        pytest.skip("Refine CLI help does not advertise a read-only status/config command")

    result = run_refine_cli(*available[0])
    assert result.returncode == 0, _combined_output(result)
    output = _combined_output(result)
    assert output.strip()
    assert str(TEST_APP_PATH.resolve()) in output
