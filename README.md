# Refine Interface Integration Smoke Suite

Standalone black-box smoke tests for Refine's browser UI, CLI, and deterministic `smoke-ai` test executable.

The suite does not import Refine source or inspect Refine's private files. It drives Refine through the same public interfaces a user would use.

## Setup

```sh
cp .env.example .env
```

Set:

```dotenv
REFINE_BASE_URL=http://127.0.0.1:8787
REFINE_PATH=/path/to/refine
REFINE_SMOKE_AI_PATH=/path/to/refine-test/tests/smoke_ai_provider_executable/smoke-ai
```

`REFINE_BASE_URL` defaults to `http://127.0.0.1:8787`. `REFINE_PATH` defaults to a sibling `../refine` checkout. `REFINE_SMOKE_AI_PATH` is set automatically by the test infrastructure, but can be overridden. Refine launches a configured provider as an executable, so this points at the `smoke-ai` executable file inside the package, not the package directory. Shell or CI environment variables override `.env`.

The infrastructure attaches the disposable app on the configured port (`uv run refine target ./test-app --port <port>`) and exports `REFINE_UI_PORT` for CLI invocations, because Refine scopes app/config discovery per port.

Install dependencies:

```sh
npm install
uv sync
```

Install Playwright browsers if needed:

```sh
npx playwright install chromium
```

## Run

```sh
uv run refine-test setup
uv run refine-test ui
uv run refine-test cli
uv run refine-test smoke-ai
uv run refine-test
uv run refine-test teardown
```

`uv run refine-test` runs every suite: the UI surface first, then the CLI surface and the smoke-ai fixture contract. The commands are scoped to surfaces (`ui`, `cli`) plus the `smoke-ai` provider contract; there is no language-level catch-all. `package.json` is kept for Playwright dependency metadata, not as the primary test runner.

Use `refine-test`, not `test`: a `test` alias exists but collides with the coreutils/shell `test`, so if its wrapper is ever missing `uv run test …` silently runs the system `test` (exit 0, no output) and appears to pass while running nothing. `refine-test` has no such collision. If `uv run refine-test` ever produces no output, reinstall the entry point with `uv pip install -e . --force-reinstall --no-deps` (a bare `uv sync` will not recreate a missing wrapper).

The CLI and UI suites create a disposable git repository at `./test-app`, attach it through `uv run refine target ./test-app --port <port>`, start Refine on `REFINE_BASE_URL`, and configure `agent_cli=smoke-ai`. Teardown stops Refine, purges the Refine test state, and removes `./test-app`. The directory is ignored by git.

Direct `smoke-ai` check:

```sh
python tests/smoke_ai_provider_executable "Say exactly the single word hello and nothing else."
```

Expected stdout:

```text
hello
```

## Data Convention

Tests use `refine-smoke` as the fixed namespace for disposable artifacts. All Refine-facing tests use the disposable `test-app` target application; workflows that create Refine data clean up the artifacts they create.

## Test Organization

Tests are organized first by public interface:

- `tests/ui`: Playwright browser tests.
- `tests/cli`: command-line tests invoked as `uv run refine <commands...>` from `REFINE_PATH`.
- `tests/smoke_ai_provider_contract`: pytest contract tests for the deterministic provider executable.
- `tests/smoke_ai_provider_executable`: the local deterministic `smoke-ai` provider executable used by UI and CLI tests.

Within each interface directory, tests should be named around user-visible outcomes once those outcomes are documented.

## Current Scope

The suite maps to the user journeys in `docs/smoke-test.md`, organized by public interface.

CLI (`uv run refine <commands...>` from `REFINE_PATH` against the disposable `test-app`):

- Local Operation (52-60): `status`, `restart`, `stop`/`start` cycle, `doctor`. Destructive or host/network-touching journeys (`install`, `uninstall`, `reset`, `update`, `test`) are verified at the command surface and not executed.
- Runtime Control (61, 65, 66): provider reporting via `doctor`, runner processes and resource metrics via `ps`.
- Multi-Node and Cluster (67, 69, 70, 74, 75): `node` list/create/activate/transfer/archive, `cluster list`, `migrate status`/`run`. Remote SSH cluster ops (`register`/`bootstrap`/`run`) are verified at the command surface.

UI (Playwright, driving the browser plus the public API for setup/verify/cleanup):

- Core shell, Navigation and Evidence, Work Intake, Gap Management, Review and Quality, Guided Setup, Application Lifecycle, Runtime Control, and Support.

Deterministic `smoke-ai`:

- Contract tests for matching, template output, JSON/JSONL parsing, and debug behavior, plus AI-driven journeys exercised through Refine (e.g. target-app instruction generation, planning chat) now that the provider is launchable.

Journeys driven by the full agent work loop (e.g. moving a Gap through agent execution to review/merge) and host/network/remote operations are intentionally out of scope for a self-contained smoke run; the suite covers the user-driven controls and states around them.
