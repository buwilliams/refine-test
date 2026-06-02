"""CLI contract for `refine target` (Application Lifecycle — attach an app).

App attachment is port-scoped (the selected app lives in `run/<port>/apps.json`),
so `target` must be told which port to attach to. The test infrastructure always
passes `--port`; this test pins the contract that the port is *mandatory*.

It is marked `xfail(strict=True)` because making `--port` required is an
in-progress Refine refactor: today the no-port form silently attaches the
default-port binding. Strict xfail keeps the suite green now and flips to a
hard failure the moment Refine starts requiring `--port` — the signal to delete
this marker and let the assertion stand on its own.
"""

from __future__ import annotations

import pytest

from tests.support.cli import combined_output, run_refine_cli
from tests.support.env import TEST_APP_PATH


pytestmark = pytest.mark.refine_cli


@pytest.mark.xfail(
    strict=True,
    reason="Refine refactor in progress: `refine target` must require --port",
)
def test_target_requires_explicit_port() -> None:
    result = run_refine_cli("target", str(TEST_APP_PATH), "--force")
    try:
        assert result.returncode != 0, combined_output(result)
        assert "port" in combined_output(result).lower()
    finally:
        # Pre-refactor, the no-port form attaches a default-port (8080) binding;
        # clear it so it does not leak into the Refine checkout. Post-refactor the
        # command fails without attaching and this is a harmless no-op.
        run_refine_cli("reset", "8080", "--yes")
