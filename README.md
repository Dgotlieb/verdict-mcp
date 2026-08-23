# verdict

**Structured, sandboxed verification feedback for coding agents.**

An [MCP](https://modelcontextprotocol.io) server that replaces your agent's `pytest` shell-outs with something built for the agent inner loop: impact-selected tests, run in an isolated environment, returning **compact typed verdicts** instead of 40,000 tokens of raw runner output — with **failure fingerprints** that tell the agent whether a failure is *its* regression or was broken all along.

```
raw pytest dump:  ~40,000 tokens, unstructured, run un-sandboxed on your machine
verdict:              ~400 tokens, typed JSON, run in a rootless container, with memory
```

## Why

The highest-frequency tool call in agentic coding is verification — and it's the least structured. Agents re-run whole suites when one module changed, burn context parsing ANSI-coded tracebacks, run arbitrary code directly on your machine, and routinely misdiagnose pre-existing breakage as their own regression (then "fix" code that wasn't broken). verdict fixes all four.

## Tools

| Tool | What it does |
|---|---|
| `verify(scope?, base?)` | Selects tests affected by your working-tree diff (static import graph via grimp), runs them via podman/docker with the worktree mounted **read-only**, returns typed failures with fingerprints and a `preexisting` flag |
| `explain_failure(check_id)` | Full traceback for one failure, on demand — bulk never rides in the summary |
| `history(fingerprint)` | First seen / last seen / times seen — regression vs. long-standing breakage |
| `run_checks(["ruff","mypy"])` | Lint and type checks, normalized into the same verdict schema |

Every failure carries a **fingerprint**: a stable hash of the normalized failure signature (volatile tokens — addresses, tmp paths, ids, durations — collapsed). Same logical failure, same fingerprint, across runs and refactors. Fingerprints are what give verdict memory.

## Quickstart

No install step needed — `uvx` fetches it on first use. (Or `uv tool install verdict-mcp` / `pip install verdict-mcp` for a permanent `verdict-mcp` command.)

**Claude Code** — `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "verdict": {
      "command": "uvx",
      "args": ["verdict-mcp"],
      "env": { "VERDICT_PROJECT": "." }
    }
  }
}
```

**Cursor** — same shape in `.cursor/mcp.json`.

Optional `verdict.toml` in your repo root:

```toml
[project]
packages = ["your_package"]          # for impact selection (auto-guessed if omitted)

[runner]
image = "ghcr.io/you/yourproj-test"  # prebuilt env with your deps
setup_cmd = "pip install -e .[test]" # or install on the fly (runs with network; tests don't)
# prefer = "local"                   # escape hatch if you have no container runtime

[limits]
max_failures = 10
```

Try it without an agent:

```bash
cd examples/demo_project
VERDICT_PROJECT=. verdict-mcp   # then connect any MCP client, or use the MCP inspector
```

## Sandbox posture (v0.1)

Checks run in an ephemeral container (podman preferred, docker fallback): worktree mounted **read-only** at `/src`, copied to a writable `/work` inside the container, `--network=none` for the check run. Your host environment is never mutated by a test run. If `setup_cmd` is configured, that step runs *with* network before the check; prefer a prebuilt image for a tighter posture. No container runtime → explicit `prefer = "local"` fallback runs checks against a temp copy of your worktree (still never in place). See [SECURITY.md](SECURITY.md) for the full threat model and known limitations.

## Honest limitations

- Impact selection uses the **static import graph** — approximate by design. Dynamic imports, fixture-by-name resolution, and data-driven tests can be missed; `verify(scope="all")` is always available and verdict says in `selection_note` whenever it falls back.
- Python/pytest only today, plus ruff/mypy. The adapter interface is small and documented — vitest and `go test -json` adapters are the most-wanted contributions ([CONTRIBUTING.md](CONTRIBUTING.md)).
- Flake detection and coverage-map-based selection are v0.2 ([roadmap](#roadmap)).

## Roadmap

**v0.2:** coverage-based impact maps (precise selection), flake detection via fingerprint alternation, devcontainer.json support, result cache keyed on (tree hash, check, image digest). **Later:** vitest/jest, go test, cargo test adapters; per-repo verdict daemon mode.

## License

Apache-2.0
