from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
SMOKE_NAMESPACE = "refine-smoke"
SMOKE_AI_PATH = ROOT / "tests" / "smoke_ai_provider_executable"
TEST_APP_PATH = ROOT / "test-app"

load_dotenv(ROOT / ".env", override=False)


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        pytest.skip(f"{name} is required; copy .env.example to .env and set it")
    return value


def refine_base_url() -> str:
    return os.environ.get("REFINE_BASE_URL", "http://127.0.0.1:8787").strip().rstrip("/")


def refine_path() -> Path:
    raw = os.environ.get("REFINE_PATH", str(ROOT.parent / "refine")).strip()
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        pytest.fail(f"REFINE_PATH does not exist: {path}")
    if not path.is_dir():
        pytest.fail(f"REFINE_PATH is not a directory: {path}")
    return path
