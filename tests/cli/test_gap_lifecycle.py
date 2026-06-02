from __future__ import annotations

import pytest

from tests.support.cli import combined_output, run_refine_cli


pytestmark = pytest.mark.refine_cli


@pytest.mark.xfail(
    strict=True,
    reason=(
        "CLI gap workflow not yet implemented; pending CLI feature parity. "
        "When this XPASSes, replace it with a real CLI Gap lifecycle test "
        "(create -> list -> move -> verify -> delete a disposable refine-smoke Gap)."
    ),
)
def test_cli_exposes_gap_workflow() -> None:
    """Gaps are currently a UI/API surface only; the CLI exposes no gap command.

    This is a tracking marker for the in-progress CLI feature-parity work: once
    the CLI advertises a gap command, the assertion passes and strict xfail flips
    to a failure, signalling that the real lifecycle test should be written.
    """
    help_result = run_refine_cli("--help")
    assert help_result.returncode == 0, combined_output(help_result)
    assert "gap" in combined_output(help_result).lower()
