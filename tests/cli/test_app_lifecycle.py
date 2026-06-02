"""CLI smoke tests for target-app management (smoke-test.md 12-18)."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

import pytest

from tests.support.cli import combined_output, parse_json_stdout, run_refine_cli
from tests.support.env import TEST_APP_PATH


pytestmark = pytest.mark.refine_cli


def test_app_list_includes_active_test_app() -> None:
    """14. Browse known apps (the swap source list)."""
    payload = parse_json_stdout(run_refine_cli("app", "list", with_port=True))
    paths = [a.get("path") for a in payload.get("apps", [])]
    assert str(TEST_APP_PATH.resolve()) in paths


def test_app_status_reports_attached_app() -> None:
    """18 (status surface). The active target app is reported."""
    payload = parse_json_stdout(run_refine_cli("app", "status", with_port=True))
    assert payload.get("attached") is True
    assert payload.get("client_repo") == str(TEST_APP_PATH.resolve())


def test_app_templates_are_listed() -> None:
    """12. Create a new application from a template (templates are offered)."""
    payload = parse_json_stdout(run_refine_cli("app", "templates"))
    templates = payload.get("templates")
    assert isinstance(templates, list) and templates


def test_app_generate_commands_with_ai() -> None:
    """17. Generate target-application commands with AI."""
    result = run_refine_cli("app", "generate", "--kind", "start", with_port=True)
    assert result.returncode == 0, combined_output(result)
    payload = parse_json_stdout(result)
    assert payload.get("ok") is True
    assert payload.get("config")


def test_app_check_reports_health_status() -> None:
    """18. Confirm the target application reports a health status."""
    # The bare test-app has no run/health commands, so `check` reports an
    # unhealthy state (non-zero exit) but still returns a structured payload.
    result = run_refine_cli("app", "check", with_port=True)
    payload = parse_json_stdout(result)
    assert isinstance(payload, dict)
    assert "state" in payload
    assert "ok" in payload


def test_app_attach_switch_remove_cycle() -> None:
    """12 + 14 + 15. Attach another app, swap back, and remove it."""
    throwaway = tempfile.mkdtemp(prefix="refine-smoke-app-")
    _git_init_app(throwaway)
    test_app = str(TEST_APP_PATH.resolve())
    try:
        attached = run_refine_cli("app", "attach", throwaway, with_port=True)
        assert attached.returncode == 0, combined_output(attached)
        status = parse_json_stdout(run_refine_cli("app", "status", with_port=True))
        assert status.get("client_repo") != test_app

        # Swap back to the disposable test-app.
        switched = run_refine_cli("app", "switch", test_app, "--force", with_port=True)
        assert switched.returncode == 0, combined_output(switched)
        final = parse_json_stdout(run_refine_cli("app", "status", with_port=True))
        assert final.get("client_repo") == test_app

        removed = run_refine_cli("app", "remove", throwaway, with_port=True)
        assert removed.returncode == 0, combined_output(removed)
        listed = parse_json_stdout(run_refine_cli("app", "list", with_port=True))
        paths = [a.get("path") for a in listed.get("apps", [])]
        assert os.path.realpath(throwaway) not in [os.path.realpath(p) for p in paths if p]
    finally:
        run_refine_cli("app", "switch", test_app, "--force", with_port=True)
        run_refine_cli("app", "remove", throwaway, with_port=True)
        shutil.rmtree(throwaway, ignore_errors=True)


def _git_init_app(path: str) -> None:
    subprocess.run(["git", "init", "-q", path], check=True)
    with open(os.path.join(path, "README.md"), "w", encoding="utf-8") as handle:
        handle.write("# refine smoke throwaway app\n")
    subprocess.run(["git", "-C", path, "add", "-A"], check=True)
    subprocess.run(
        [
            "git", "-C", path,
            "-c", "user.email=refine-smoke@example.invalid",
            "-c", "user.name=Refine Smoke",
            "commit", "-q", "-m", "init",
        ],
        check=True,
    )
