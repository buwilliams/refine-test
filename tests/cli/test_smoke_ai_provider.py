from __future__ import annotations

import pytest

from tests.support.cli import run_refine_cli
from tests.support.env import SMOKE_AI_PATH


pytestmark = pytest.mark.refine_cli


def _combined_output(result) -> str:
    return f"{result.stdout}\n{result.stderr}"


def test_cli_reports_smoke_ai_provider_when_supported() -> None:
    result = run_refine_cli("doctor")
    output = _combined_output(result)
    assert "No refine configuration found" not in output
    assert "smoke-ai" in output, f"expected smoke-ai provider from {SMOKE_AI_PATH}"
