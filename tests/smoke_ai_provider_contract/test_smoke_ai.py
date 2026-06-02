from __future__ import annotations

import json
import os
import subprocess

import pytest

from tests.support.cli import smoke_ai_script


pytestmark = pytest.mark.smoke_ai


def run_smoke_ai(*args: str, stdin: str | None = None, debug: bool = False) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if debug:
        env["SMOKE_AI_DEBUG"] = "1"
    return subprocess.run(
        ["python", str(smoke_ai_script()), *args],
        input=stdin,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def test_unknown_flags_exit_zero() -> None:
    result = run_smoke_ai("--unknown", "--another-flag")
    assert result.returncode == 0
    assert result.stdout


def test_preflight_prompt_returns_exactly_hello() -> None:
    result = run_smoke_ai("Say exactly the single word hello and nothing else.")
    assert result.returncode == 0
    assert result.stdout == "hello\n"


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Start a chat about a product defect.", "smoke-ai chat response"),
        ("Run the gap agent for a ready Gap.", "smoke-ai gap-agent response"),
        ("Import these CSV rows into gaps.", '"kind": "import"'),
        ("Check the target app and report health.", '"kind": "target-app"'),
        ("Generate governance rules for this project.", "smoke-ai governance response"),
        ("Completely unrelated prompt.", "smoke-ai fallback response"),
    ],
)
def test_matchers_select_expected_templates(prompt: str, expected: str) -> None:
    result = run_smoke_ai(prompt)
    assert result.returncode == 0
    assert expected in result.stdout


def test_stdin_participates_in_matching() -> None:
    result = run_smoke_ai(stdin="Please import this markdown list into Refine.")
    assert result.returncode == 0
    assert '"kind": "import"' in result.stdout


def test_json_template_emits_verbatim_and_parses() -> None:
    result = run_smoke_ai("Check the target app status.")
    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert parsed["kind"] == "target-app"
    assert parsed["ok"] is True


def test_jsonl_template_emits_verbatim_and_parses() -> None:
    result = run_smoke_ai("Import these issues.")
    assert result.returncode == 0
    lines = [json.loads(line) for line in result.stdout.splitlines()]
    assert [line["kind"] for line in lines] == ["import", "import"]


def test_debug_mode_does_not_alter_stdout() -> None:
    normal = run_smoke_ai("Run the gap agent.")
    debug = run_smoke_ai("Run the gap agent.", debug=True)
    assert normal.stdout == debug.stdout
    assert debug.stderr
