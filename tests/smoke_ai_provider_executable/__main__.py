from __future__ import annotations

import os
import sys
from pathlib import Path


TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

MATCHERS: list[tuple[str, tuple[str, ...], str]] = [
    (
        "preflight",
        (
            "single word hello",
            "exactly the single word hello",
            "say exactly",
            "preflight",
        ),
        "preflight.md",
    ),
    ("gap-agent", ("gap agent", "ready gap", "work on gap"), "gap-agent.md"),
    ("import", ("import", "csv", "rows", "dedup"), "import.jsonl"),
    ("target-app", ("target app", "health", "start command", "rebuild"), "target-app.json"),
    ("governance", ("governance", "constitution", "rules"), "governance.md"),
    ("chat", ("chat", "conversation", "message", "defect"), "chat.md"),
]


def main() -> int:
    prompt = " ".join(arg for arg in sys.argv[1:] if arg)
    stdin = ""
    if not sys.stdin.isatty():
        stdin = sys.stdin.read()
    haystack = f"{prompt}\n{stdin}".lower()

    selected_name = "fallback"
    selected_template = "fallback.md"
    for name, needles, template in MATCHERS:
        if any(needle in haystack for needle in needles):
            selected_name = name
            selected_template = template
            break

    if os.environ.get("SMOKE_AI_DEBUG") == "1":
        print(f"smoke-ai matcher={selected_name} template={selected_template}", file=sys.stderr)

    output = (TEMPLATE_DIR / selected_template).read_text(encoding="utf-8")
    sys.stdout.write(output)
    if not output.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
