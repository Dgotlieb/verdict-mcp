# Contributing

The most valuable contribution to verdict right now is a **new check adapter**. The interface is deliberately small.

## Adding an adapter

An adapter is one module in `src/verdict_mcp/adapters/` providing:

1. `command(paths: list[str]) -> list[str]` — the CLI invocation, writing any report file to `$VERDICT_ARTIFACTS/` (expanded by the runner).
2. A parser: `parse_*(...) -> list[Failure]` (see `schema.py`). Populate `check_id` (stable, prefixed with your runner name), `message` (one line, ≤300 chars), `location`, and compute the fingerprint via `fingerprint(check_id, error_type, message)`.

Ground rules that keep verdict being verdict:

- **Summaries stay small.** Anything bulky goes into `FailureDetail` behind `explain_failure`, never into the `verify` payload.
- **Fingerprints must be stable.** Normalize volatile tokens (see `fingerprint.py`); add normalizer patterns there if your runner emits new kinds of noise, with a test proving two volatile variants collapse.
- **Structured over parsed.** Prefer a runner's native JSON output (`--json`, reporter plugins) over scraping text. If only text exists, parse defensively and test against a real captured fixture, not a hand-written one.

Most-wanted adapters: vitest (`--reporter=json`), `go test -json`, `cargo test` (libtest JSON), jest.

## Dev setup

```bash
uv venv && uv pip install -e ".[dev]"
uv run pytest
```

Fixtures under `tests/fixtures/` are generated from real runner output (see the comment in each test). Regenerate rather than hand-edit.

## Style

Ruff, line length 100. Small PRs over big ones. A failing-then-passing test tells the story better than the PR description.
