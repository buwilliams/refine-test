from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
TEST_APP_PATH = ROOT / "test-app"
SMOKE_AI_PATH = ROOT / "tests" / "smoke_ai_provider_executable"
# Refine launches a configured provider as `[binary_path, prompt]`, so it must be
# pointed at a directly-executable file, not the package directory.
SMOKE_AI_EXECUTABLE = SMOKE_AI_PATH / "smoke-ai"
DEFAULT_BASE_URL = "http://127.0.0.1:8787"
DEFAULT_REFINE_PATH = ROOT.parent / "refine"

load_dotenv(ROOT / ".env", override=False)


class InfrastructureError(RuntimeError):
    pass


def base_url() -> str:
    return os.environ.get("REFINE_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")


def port() -> int:
    parsed = urlparse(base_url())
    if parsed.port is not None:
        return parsed.port
    if parsed.scheme == "https":
        return 443
    return 80


def refine_path() -> Path:
    raw = os.environ.get("REFINE_PATH", "").strip()
    path = Path(raw).expanduser() if raw else DEFAULT_REFINE_PATH
    path = path.resolve()
    if not path.is_dir():
        raise InfrastructureError(
            f"REFINE_PATH does not point to a Refine checkout: {path}"
        )
    return path


def configure_process_env() -> None:
    os.environ.setdefault("REFINE_BASE_URL", DEFAULT_BASE_URL)
    os.environ.setdefault("REFINE_PATH", str(refine_path()))
    os.environ["REFINE_SMOKE_AI_PATH"] = str(SMOKE_AI_EXECUTABLE)


def subprocess_env() -> dict[str, str]:
    configure_process_env()
    env = os.environ.copy()
    env["REFINE_SMOKE_AI_PATH"] = str(SMOKE_AI_EXECUTABLE)
    # Config/app discovery is port-scoped (run/<port>/apps.json). Pin the configured
    # port so CLI commands without a PORT argument (e.g. doctor) resolve the test-app
    # binding instead of defaulting to the empty default-port binding.
    env["REFINE_UI_PORT"] = str(port())
    return env


def run_refine_cli(*args: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["uv", "run", "refine", *args],
        cwd=refine_path(),
        env=subprocess_env(),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return result


def ensure_test_app() -> None:
    TEST_APP_PATH.mkdir(parents=True, exist_ok=True)
    (TEST_APP_PATH / "README.md").write_text(
        "# Refine smoke target app\n\nDisposable target app for refine-test.\n",
        encoding="utf-8",
    )
    (TEST_APP_PATH / "app.py").write_text(
        "def health() -> str:\n"
        "    return \"ok\"\n",
        encoding="utf-8",
    )
    (TEST_APP_PATH / ".gitignore").write_text(
        "__pycache__/\n"
        "*.py[cod]\n",
        encoding="utf-8",
    )

    if not (TEST_APP_PATH / ".git").is_dir():
        _run(["git", "init", "-q"], cwd=TEST_APP_PATH)
    _run(["git", "config", "user.email", "refine-smoke@example.invalid"], cwd=TEST_APP_PATH)
    _run(["git", "config", "user.name", "Refine Smoke"], cwd=TEST_APP_PATH)
    _run(["git", "add", "README.md", "app.py", ".gitignore"], cwd=TEST_APP_PATH)
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--exit-code"],
        cwd=TEST_APP_PATH,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if staged.returncode == 1:
        _run(["git", "commit", "-q", "-m", "Initialize refine smoke target app"], cwd=TEST_APP_PATH)
    elif staged.returncode != 0:
        raise InfrastructureError(_format_cli_failure("git diff --cached", staged))


def setup() -> None:
    configure_process_env()
    ensure_test_app()
    run_refine_cli("stop", str(port()), timeout=30)

    target = run_refine_cli(
        "target", str(TEST_APP_PATH), "--port", str(port()), "--force", timeout=60
    )
    if target.returncode != 0:
        raise InfrastructureError(_format_cli_failure("refine target", target))

    set_refine_setting("agent_cli", "smoke-ai")

    started = run_refine_cli("start", str(port()), timeout=90)
    if started.returncode != 0:
        raise InfrastructureError(_format_cli_failure("refine start", started))

    status = wait_for_project_status()
    actual_app = str(status.get("client_repo") or "")
    if actual_app != str(TEST_APP_PATH.resolve()):
        raise InfrastructureError(
            f"Refine is attached to {actual_app or '<none>'}, expected {TEST_APP_PATH.resolve()}"
        )

    settings = patch_settings({"agent_cli": "smoke-ai"})
    agent_cli = str(settings.get("agent_cli") or "")
    if agent_cli != "smoke-ai":
        raise InfrastructureError(f"agent_cli is {agent_cli!r}, expected 'smoke-ai'")


def set_refine_setting(key: str, value: str) -> None:
    env = subprocess_env()
    env["REFINE_SETTING_KEY"] = key
    env["REFINE_SETTING_VALUE"] = value
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-c",
            (
                "import os\n"
                "from refine_server import config, db\n"
                "cfg = config.get(reload=True)\n"
                "db.init_db(cfg.sqlite_path)\n"
                "conn = db.connect(cfg.sqlite_path)\n"
                "try:\n"
                "    db.set_setting(conn, os.environ['REFINE_SETTING_KEY'], os.environ['REFINE_SETTING_VALUE'])\n"
                "finally:\n"
                "    conn.close()\n"
            ),
        ],
        cwd=refine_path(),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise InfrastructureError(_format_cli_failure(f"set Refine setting {key}", result))


def teardown() -> None:
    configure_process_env()
    run_refine_cli("stop", str(port()), timeout=30)
    run_refine_cli("reset", "--purge", "--yes", timeout=60)
    if TEST_APP_PATH.exists():
        shutil.rmtree(TEST_APP_PATH)
    deadline = time.monotonic() + 3.0
    while TEST_APP_PATH.exists() and time.monotonic() < deadline:
        shutil.rmtree(TEST_APP_PATH, ignore_errors=True)
        time.sleep(0.2)
    if TEST_APP_PATH.exists():
        raise InfrastructureError(f"could not remove {TEST_APP_PATH}")


def wait_for_project_status(timeout: float = 30.0) -> dict:
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        try:
            response = requests.get(f"{base_url()}/api/project/status", timeout=2)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and data.get("attached") is True:
                    return data
            last_error = response.text
        except (requests.RequestException, ValueError) as exc:
            last_error = str(exc)
        time.sleep(0.5)
    raise InfrastructureError(f"Refine API did not become ready at {base_url()}: {last_error}")


def patch_settings(values: dict[str, str]) -> dict:
    response = requests.patch(f"{base_url()}/api/settings", json=values, timeout=15)
    if response.status_code != 200:
        raise InfrastructureError(
            f"PATCH /api/settings failed with {response.status_code}: {response.text}"
        )
    data = response.json()
    settings = data.get("settings")
    if not isinstance(settings, dict):
        readback = requests.get(f"{base_url()}/api/settings", timeout=15)
        if readback.status_code != 200:
            raise InfrastructureError(
                f"GET /api/settings failed with {readback.status_code}: {readback.text}"
            )
        settings = readback.json().get("settings")
    if not isinstance(settings, dict):
        raise InfrastructureError("Refine settings response did not contain a settings object")
    return settings


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise InfrastructureError(_format_cli_failure(" ".join(command), result))
    return result


def _format_cli_failure(label: str, result: subprocess.CompletedProcess[str]) -> str:
    return (
        f"{label} failed with exit code {result.returncode}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage refine-test infrastructure.")
    parser.add_argument("command", choices=("setup", "teardown", "status"))
    args = parser.parse_args(argv)

    if args.command == "setup":
        setup()
        print(f"Refine test infrastructure ready at {base_url()} using {TEST_APP_PATH}")
        return 0
    if args.command == "teardown":
        teardown()
        print("Refine test infrastructure removed")
        return 0

    status = wait_for_project_status(timeout=5)
    settings = requests.get(f"{base_url()}/api/settings", timeout=15).json()["settings"]
    print(f"base_url={base_url()}")
    print(f"client_repo={status.get('client_repo')}")
    print(f"agent_cli={settings.get('agent_cli')}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except InfrastructureError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
