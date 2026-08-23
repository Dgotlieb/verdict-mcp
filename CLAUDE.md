# verdict — project context for Claude Code

## What this is

An MCP server giving coding agents structured, sandboxed test feedback: impact-selected pytest runs in ephemeral containers, returning compact typed verdicts (~400 tokens instead of ~40k of raw output) with stable failure fingerprints and history ("is this failure pre-existing or my regression?"). Built as an open-source credibility project for an advanced technical curriculum. Full roadmap: `docs/build-plan.md`. Immediate next steps: `TODO-next.md`.

## Architecture map

- `src/verdict_mcp/server.py` — FastMCP surface: `verify`, `explain_failure`, `history`, `run_checks`
- `core.py` — orchestration behind the tools (import-friendly, tested directly)
- `impact.py` — grimp import-graph test selection; honest fallback to full suite with `selection_note`
- `runner/` — execution backends: `container.py` (podman preferred, docker fallback; worktree read-only at /src, copy to /work, --network=none) and `local.py` (temp-copy fallback, never in-place)
- `adapters/` — pytest (via pytest-json-report), ruff, mypy → normalized `Failure` objects
- `fingerprint.py` — normalized failure hashing (volatile tokens collapsed); fingerprints power history
- `history.py` — SQLite (`.verdict/history.db`): preexisting detection, failure details, run summaries
- `schema.py` — the verdict contract; `examples/demo_project/` — test fixture project (one intentional failure)

## Commands

```bash
uv run pytest -q                 # full suite (20 tests; 2 are @container and skip without a live engine)
uv run ruff check src tests     # lint
```

On this Mac (macOS 12, x86_64) `uv run`/`uv sync` fail because `cryptography>=49` (pulled in by fastmcp) ships no wheel for the platform. The lockfile is left alone for CI; locally use `.venv/bin/python -m pytest -q` / `.venv/bin/ruff check src tests`, and (re)create the env with:

```bash
uv pip install --python .venv/bin/python -e ".[dev]" anyio "cryptography<49"
```

## Design rules (do not violate)

1. **Summaries stay small.** Nothing bulky in the `verify` payload — full tracebacks go in `FailureDetail` behind `explain_failure`.
2. **Fingerprints must be stable** across runs/refactors. New volatile-token patterns get a normalizer in `fingerprint.py` plus a test proving two variants collapse.
3. **Never mutate the host worktree.** Every runner executes against a read-only mount or a temp copy.
4. **Honest degradation.** When selection falls back to the full suite, say why in `selection_note`. No silent approximations.
5. Structured runner output (JSON reporters) over text scraping. Fixtures are captured from real runs, never hand-written.

## Current state / known gaps

- Scaffolded 2026-08-23 in a cloud sandbox; 17 tests green, ruff clean.
- **`ContainerRunner` verified against Docker Desktop** (2026-08-23). Two bugs fixed on first run: `detect_engine` now requires `<engine> info` to succeed (a podman binary with a stopped VM was being chosen over a live docker), and `$VERDICT_ARTIFACTS` is resolved to `/artifacts` before shell-quoting (quoting had suppressed expansion, so the JSON report never reached the artifacts mount). `tests/test_container_runner.py` builds `verdict-test-py312:local` once per session and runs `verify_core` through the real engine with `--network=none`.
- Parked for v0.2 (don't reopen early): coverage-based selection, flake detection, container resource limits, non-Python adapters.
