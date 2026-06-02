"""CLI smoke tests for the "Local Operation" journeys (smoke-test.md 52-60).

These drive `uv run refine <command>` from REFINE_PATH against the disposable
test-app, the same way a user would operate a local Refine checkout. Journeys
that are destructive to the shared instance (reset binding) or that touch the
host/network (systemd install/uninstall, self-update, full test suite) are
verified at the command-surface level and skipped before execution so the smoke
run stays self-contained.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time

import pytest
import requests

from tests.support.cli import combined_output, configured_port, run_refine_cli
from tests.support.env import TEST_APP_PATH, refine_base_url


# A throwaway port for the persistent-service test, distinct from the smoke
# instance's port so installing/uninstalling a systemd unit never disturbs it.
INSTALL_TEST_PORT = "8099"


def _systemd_service_management_available() -> tuple[bool, str]:
    """Installing a *system* service needs systemd plus root/passwordless sudo.

    This is an OS prerequisite, not a Refine concern: `refine install` writes to
    /etc/systemd/system and runs `systemctl enable/start`. When the prerequisite
    is absent (e.g. an unprivileged sandbox) the test skips; on CI/root it runs
    for real.
    """
    if shutil.which("systemctl") is None:
        return False, "systemctl is not available"
    try:
        subprocess.run(
            ["systemctl", "is-system-running"], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"systemd is not usable: {exc}"
    if os.geteuid() != 0:
        probe = subprocess.run(["sudo", "-n", "true"], capture_output=True, text=True)
        if probe.returncode != 0:
            return False, "installing a system service needs root or passwordless sudo"
    return True, ""


def _port_responds(port: str) -> bool:
    try:
        requests.get(f"http://127.0.0.1:{port}/api/project/status", timeout=2)
        return True
    except requests.RequestException:
        return False


pytestmark = pytest.mark.refine_cli


def _wait_for_api(timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        try:
            response = requests.get(f"{refine_base_url()}/api/project/status", timeout=2)
            if response.status_code == 200 and response.json().get("attached") is True:
                return
            last = response.text
        except (requests.RequestException, ValueError) as exc:
            last = str(exc)
        time.sleep(0.5)
    raise AssertionError(f"Refine API did not return to healthy: {last}")


def test_status_reports_attached_test_app() -> None:
    """52. Check Refine status from the CLI."""
    result = run_refine_cli("status", configured_port())
    assert result.returncode == 0, combined_output(result)
    output = combined_output(result)
    assert configured_port() in output
    assert str(TEST_APP_PATH.resolve()) in output


def test_restart_returns_instance_to_healthy() -> None:
    """53. Restart Refine from the CLI."""
    result = run_refine_cli("restart", configured_port(), timeout=90)
    assert result.returncode == 0, combined_output(result)
    _wait_for_api()


def test_stop_then_start_cycle_restores_service() -> None:
    """54. Stop Refine from the CLI (and bring it back for the rest of the run)."""
    try:
        stopped = run_refine_cli("stop", configured_port(), timeout=60)
        assert stopped.returncode == 0, combined_output(stopped)
    finally:
        started = run_refine_cli("start", configured_port(), timeout=90)
        assert started.returncode == 0, combined_output(started)
    _wait_for_api()


def test_doctor_runs_diagnostics() -> None:
    """58. Run Refine diagnostics."""
    result = run_refine_cli("doctor", timeout=60)
    output = combined_output(result)
    assert "No refine configuration found" not in output, output
    assert str(TEST_APP_PATH.resolve()) in output
    # The diagnostic snapshot is organized into labelled sections.
    assert "Configuration" in output
    assert "Agent CLI" in output


def test_install_then_uninstall_persistent_service() -> None:
    """55 + 56. Install Refine as a persistent service, then uninstall it.

    Runs a real install -> verify-listening -> uninstall -> verify-gone cycle on
    a dedicated port, and always cleans up the unit and run state.
    """
    available, reason = _systemd_service_management_available()
    if not available:
        pytest.skip(reason)

    uninstalled = False
    installed = run_refine_cli("install", INSTALL_TEST_PORT, timeout=180)
    try:
        assert installed.returncode == 0, combined_output(installed)
        # `install` blocks until the managed service is listening, so a healthy
        # port confirms systemd actually brought the service up.
        assert _port_responds(INSTALL_TEST_PORT), combined_output(installed)

        result = run_refine_cli("uninstall", INSTALL_TEST_PORT, timeout=180)
        uninstalled = True
        assert result.returncode == 0, combined_output(result)

        deadline = time.monotonic() + 15
        while _port_responds(INSTALL_TEST_PORT) and time.monotonic() < deadline:
            time.sleep(0.5)
        assert not _port_responds(INSTALL_TEST_PORT), "service still listening after uninstall"
    finally:
        if not uninstalled:
            run_refine_cli("uninstall", INSTALL_TEST_PORT, timeout=180)
        run_refine_cli("reset", INSTALL_TEST_PORT, "--yes", timeout=60)


@pytest.mark.parametrize(
    ("command", "journey"),
    [
        ("reset", "57. Reset the local Refine binding"),
        ("update", "60. Update Refine to the latest release"),
        ("test", "59. Run the repository test suite"),
    ],
)
def test_local_operation_command_is_advertised(command: str, journey: str) -> None:
    """Remaining destructive/network journeys: confirm the command surface exists.

    Executing these would reach the network (self-update), detach the shared
    test-app (reset), or recursively run the entire Refine suite (test). The
    smoke check verifies the command is advertised and documents its own help
    instead of running it.
    """
    help_result = run_refine_cli("--help")
    assert help_result.returncode == 0, combined_output(help_result)
    assert command in combined_output(help_result).lower(), journey

    command_help = run_refine_cli(command, "--help")
    assert command_help.returncode == 0, combined_output(command_help)
    assert command in combined_output(command_help).lower()
