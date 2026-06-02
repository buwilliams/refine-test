# refine-test

refine-test is a standalone black-box smoke suite for [refine](https://github.com/buwilliams/refine) — its browser UI, its CLI, and its deterministic `smoke-ai` test provider. It never imports Refine source or inspects Refine's private files; it drives Refine through the same public interfaces a person would use and verifies the user journeys catalogued in `docs/smoke-test.md`.

- **Black-box** - exercises Refine through its public UI, CLI, and HTTP API only — no source imports, no private-file inspection.
- **Three surfaces** - Playwright browser tests, CLI tests invoked as `uv run refine <commands…>`, and a contract for the deterministic provider.
- **Disposable and self-cleaning** - each run attaches a throwaway `test-app`, exercises it, and tears everything down; tests clean up the data they create.
- **Deterministic AI** - a local `smoke-ai` executable returns repeatable responses, so AI-driven journeys (planning chat, command generation, imports) run without a real model.
- **Journey-mapped** - tests are organized by interface and named around the user goals in `docs/smoke-test.md`.

## Quick Start

Requires a sibling `refine` checkout, Python (via [`uv`](https://docs.astral.sh/uv/)), and Node (for Playwright).

```sh
cp .env.example .env   # then edit REFINE_BASE_URL and REFINE_PATH
npm install
uv sync
npx playwright install chromium
```

Run every suite — the UI surface first, then the CLI surface and the smoke-ai contract:

```sh
uv run refine-test
```

Or target a single surface:

```sh
uv run refine-test setup      # attach a disposable test-app and start Refine
uv run refine-test ui         # Playwright UI tests
uv run refine-test cli        # CLI tests
uv run refine-test smoke-ai   # deterministic provider contract
uv run refine-test teardown   # stop Refine and remove all test state
```

refine-test has its own runner:

```sh
uv run refine-test --help
```

Use `refine-test`, not the `test` alias: `test` collides with the shell/coreutils `test`, so if its wrapper is ever missing, `uv run test …` silently runs the system binary (exit 0, no output) and the suite appears to pass while running nothing. If `uv run refine-test` ever prints nothing, reinstall the entry point with `uv pip install -e . --force-reinstall --no-deps` (a bare `uv sync` will not recreate a missing wrapper).

## Configuration

Settings live in `.env`; shell or CI environment variables override it.

```dotenv
REFINE_BASE_URL=http://127.0.0.1:8787
REFINE_PATH=/path/to/refine
REFINE_SMOKE_AI_PATH=/path/to/refine-test/tests/smoke_ai_provider_executable/smoke-ai
```

- `REFINE_BASE_URL` — where Refine serves; defaults to `http://127.0.0.1:8787`.
- `REFINE_PATH` — the Refine checkout to drive; defaults to a sibling `../refine`.
- `REFINE_SMOKE_AI_PATH` — set automatically by the infrastructure. Refine launches a provider as an executable, so this points at the `smoke-ai` executable file inside the package, not the package directory.

`setup` attaches the disposable `test-app` on the configured port, starts Refine, and configures `agent_cli=smoke-ai`; `teardown` stops Refine, purges the test state, and removes `./test-app` (which is git-ignored). `package.json` is kept for Playwright dependency metadata, not as the primary runner.

Refine CLI commands target the configured port (default 8080) unless a port is explicitly passed. The suite runs on a non-default port, so the infrastructure exports `REFINE_UI_PORT` as the configured port for commands that take no port argument, and the tests pass an explicit port (positional for runtime commands, `--port` for data commands) to every command that accepts one.

## Test Organization

Tests are organized first by public interface:

- `tests/ui` — Playwright browser tests.
- `tests/cli` — CLI tests invoked as `uv run refine <commands…>` from `REFINE_PATH`.
- `tests/smoke_ai_provider_contract` — pytest contract for the deterministic provider.
- `tests/smoke_ai_provider_executable` — the local `smoke-ai` provider used by the UI and CLI suites.

Within each directory, tests are named around user-visible outcomes. They use `refine-smoke` as the fixed namespace for disposable artifacts, run against the disposable `test-app`, and clean up what they create.

The provider can be exercised directly:

```sh
python tests/smoke_ai_provider_executable "Say exactly the single word hello and nothing else."
# -> hello
```

## Coverage

The suite maps to the journeys in `docs/smoke-test.md`:

- **CLI** (full parity with the UI) — Gap management and workflow, work intake (reporters, import), chat, application lifecycle, runtime control and processes, local operation, and multi-node/cluster.
- **UI** (Playwright, plus the public API for setup/verify/cleanup) — app shell, navigation and evidence, work intake, gap management, review and quality, guided setup, application lifecycle, runtime control, and support.
- **smoke-ai** — provider matching, template/JSON/JSONL output and debug behavior, plus AI-driven journeys exercised through Refine.

Journeys that require the full agent work loop (driving a Gap through agent execution to merge) or host/network/remote operations (systemd install, self-update, SSH cluster) are out of scope for a self-contained run; the suite covers the user-driven controls and states around them, and verifies those commands at the surface.

## License

[MIT](https://github.com/buwilliams/refine/blob/main/LICENSE), same as refine.
