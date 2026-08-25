# Anatomy of an MCP verification server

*First post in a build-in-public series about [verdict](https://github.com/Dgotlieb/verdict-mcp), an MCP server that gives coding agents structured, sandboxed test feedback.*

## The problem

Watch a coding agent work and you'll see it run `pytest` in your shell, unsandboxed, and then push 40,000 tokens of raw output through its context window to answer one question: *did my change break anything?*

That's three problems in one command:

1. **Token waste.** The agent needs ~10 lines of signal and pays for a wall of dots, warnings, and tracebacks.
2. **No sandbox.** The tests run on your machine, in your environment, with your files writable.
3. **No memory.** When a test fails, the agent can't tell whether *it* broke it or whether it was broken before it arrived — so it either "fixes" pre-existing failures nobody asked about, or ships regressions it assumes were already there.

verdict is an MCP server that replaces the pytest shell-out with four tools:

| tool | what it returns |
|---|---|
| `verify(scope?)` | impact-selected tests, run in an ephemeral container, as a ~400-token typed verdict |
| `explain_failure(check_id)` | the full traceback — only on demand |
| `history(fingerprint)` | first seen / last seen / times seen for a failure |
| `run_checks(["ruff","mypy"])` | lint & type checks, same verdict shape |

## The three ideas

**1. Verdicts, not output.** `verify` returns typed JSON: counts, per-failure message + location, and nothing else. Full tracebacks live behind `explain_failure`. The whole verdict for a real failing run is ~400 tokens — the raw pytest output it replaces was ~40k. The design rule in the repo is blunt: *nothing bulky rides in the summary, ever.*

**2. Fingerprints give failures identity.** Every failure is hashed from its *normalized* signature — volatile tokens (addresses, tmp paths, ids, durations) collapsed first. Same logical failure ⇒ same fingerprint, across runs and refactors. Fingerprints are what make the third idea possible:

**3. History answers "was it me?"** verdict keeps a small SQLite db per project. Every failure in a verdict carries `preexisting: true|false` — *this exact failure was known before your change* vs. *never seen it, it's yours*. In the demo session that flag is the difference between an agent politely ignoring long-standing breakage and an agent burning a session "fixing" it.

## Sandboxing posture (v0.1, honest version)

Checks run in an ephemeral container (podman preferred, docker fallback, auto-detected — with liveness checks, because a podman binary with a stopped VM is worse than no podman at all). The worktree is mounted **read-only** at `/src`, copied to a writable `/work` inside, and the check run gets `--network=none`. Configured `setup_cmd` runs *with* network before the check; a prebuilt image is the tighter posture. No engine? An explicit `prefer = "local"` fallback still runs against a temp copy — and if verdict ever runs somewhere other than where you configured, it says so in the verdict (`runner_note`). No silent degradation is a design rule.

Known gaps are written down in SECURITY.md rather than hand-waved: no resource limits yet, `setup_cmd` is network-open by design.

## What dogfooding found (the embarrassing part)

I wired verdict into Claude Code and asked it to fix a bug. Two things surfaced in the first hour that the 26-test suite had missed:

- **Impact selection had never actually run.** The server ships as a console script, so the target project was never importable from its venv — grimp couldn't build the import graph, and selection silently(-ish) fell back to the full suite every time. My own test had papered over this with a `sys.path` hack and an "honest fallback is acceptable" escape hatch. Deleted both, fixed for real.
- **Every scoped run executed the whole suite.** `pytest --json-report-omit` takes `nargs='+'`… and the test paths came right after it. pytest swallowed them as omit values. Ten characters of argument reordering.

Both bugs made the headline feature a no-op while all tests were green. The suite now has the tests that would have caught them — written by breaking the real thing first.

## Numbers from a real repo

Cloned python-dotenv (255 tests), dropped in a two-line `verdict.toml`, no other changes:

- full suite in a container, deps installed on the fly: 255 tests, green, ~146s (dominated by `pip install`)
- touch one hub module (`variables.py`) → impact selection runs 184 tests, skips ~70, and says exactly how approximate the selection is in `selection_note`

That 146s is the next mountain: env setup needs caching (image reuse keyed on deps, result cache keyed on tree hash) before verify feels instant. That's v0.2, and it's written down as v0.2 — scope discipline is also a feature.

## Try it

```json
{ "mcpServers": { "verdict": { "command": "uvx", "args": ["verdict-mcp"], "env": { "VERDICT_PROJECT": "." } } } }
```

`pip install verdict-mcp` / `uvx verdict-mcp`. Apache-2.0. Demo video and the full threat model in the [repo](https://github.com/Dgotlieb/verdict-mcp).
