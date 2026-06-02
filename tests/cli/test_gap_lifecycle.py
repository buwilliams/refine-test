from __future__ import annotations

import pytest

from tests.support.cli import run_refine_cli
from tests.support.env import SMOKE_NAMESPACE


pytestmark = pytest.mark.refine_cli


def _combined_output(result) -> str:
    return f"{result.stdout}\n{result.stderr}"


def test_cli_exposes_disposable_gap_workflow_when_supported() -> None:
    help_result = run_refine_cli("--help")
    assert help_result.returncode == 0, _combined_output(help_result)
    help_text = _combined_output(help_result).lower()
    if "gap" not in help_text:
        pytest.skip(f"Refine CLI does not currently expose a public {SMOKE_NAMESPACE} Gap workflow")
