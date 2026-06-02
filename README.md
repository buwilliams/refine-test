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
REFINE_SMOKE_AI_PATH=/path/to/refine-test/tests/smoke_ai_provider_executable
```

`REFINE_BASE_URL` defaults to `http://127.0.0.1:8787`. `REFINE_PATH` defaults to a sibling `../refine` checkout. `REFINE_SMOKE_AI_PATH` is set automatically by the test infrastructure, but can be overridden. Shell or CI environment variables override `.env`.

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
uv run test setup
uv run test ui
uv run test cli
uv run test smoke-ai
uv run test python
uv run test
uv run test teardown
```

`uv run test` runs the UI suite first, then the Python suites. `package.json` is kept for Playwright dependency metadata, not as the primary test runner.

The CLI and UI suites create a disposable git repository at `./test-app`, attach it through `uv run refine target ./test-app --force`, start Refine on `REFINE_BASE_URL`, and configure `agent_cli=smoke-ai`. Teardown stops Refine, purges the Refine test state, and removes `./test-app`. The directory is ignored by git.

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

The smoke suite covers:

- UI shell rendering and Playwright-observed browser/runtime errors.
- CLI help plus status/doctor checks invoked as `uv run refine <commands...>` from `REFINE_PATH` against the disposable `test-app`.
- Deterministic `smoke-ai` matching, template output, JSON/JSONL parsing, and debug behavior.

`smoke-ai` provider configuration checks require production Refine to report `agent_cli=smoke-ai` through public CLI/UI surfaces.
