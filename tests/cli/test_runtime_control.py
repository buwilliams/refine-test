"""CLI smoke tests for the "Runtime Control" journeys (smoke-test.md 61-66)
that have a command-line surface.

Provider configuration is observable through `refine doctor`; runner processes
and runtime performance metrics are observable through `refine ps`. Pause/unpause
scheduling, runtime limits, and stopping stale processes are driven through the
UI/API and are covered by the Playwright specs.
"""

from __future__ import annotations

import pytest

from tests.support.cli import combined_output, configured_port, run_refine_cli
from tests.support.env import SMOKE_AI_PATH, TEST_APP_PATH


pytestmark = pytest.mark.refine_cli


def test_doctor_reports_configured_provider_and_auth_probe() -> None:
    """61. Configure the AI provider and re-check authentication.

    `doctor` is the read-only surface that reports the active provider and the
    result of probing it (the auth/version check). The smoke provider is
    configured by the test infrastructure, so doctor must name it.
    """
    result = run_refine_cli("doctor", timeout=60)
    output = combined_output(result)
    assert "Agent CLI" in output, output
    assert "smoke-ai" in output, f"expected smoke-ai provider from {SMOKE_AI_PATH}\n{output}"
    # doctor probes the provider; the probe line is reported regardless of result.
    assert "--version" in output, output


def test_ps_reports_runner_processes() -> None:
    """65. Inspect runner processes and background jobs."""
    result = run_refine_cli("ps", configured_port(), timeout=60)
    assert result.returncode == 0, combined_output(result)
    output = combined_output(result)
    assert configured_port() in output
    assert str(TEST_APP_PATH.resolve()) in output
    assert "process(es)" in output


def test_ps_reports_resource_metrics() -> None:
    """66. View and filter runtime performance metrics."""
    result = run_refine_cli("ps", configured_port(), timeout=60)
    assert result.returncode == 0, combined_output(result)
    output = combined_output(result)
    # The snapshot totals line reports CPU and memory for the running processes.
    assert "totals:" in output
    assert "CPU" in output
    assert "RSS" in output
