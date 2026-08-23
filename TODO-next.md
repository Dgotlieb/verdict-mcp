# Next session — start here

Per the build plan: never start a session without a pre-written first task.

## Immediate (session 1 on your machine)

1. ~~First real container run.~~ **Done 2026-08-23** — see `tests/test_container_runner.py` and the
   "Current state" notes in CLAUDE.md. Both configurations work: a prebuilt `image` (check run is
   `--network=none`, ~2s) and plain `python:3.12-slim` + `setup_cmd = "pip install pytest pytest-json-report"`
   (~10s). Note: `uv run` is broken on this Mac (cryptography wheels); use `.venv/bin/python -m pytest`.
2. **Wire into Claude Code for a dogfood run:** `.mcp.json` per README, then ask the agent to break/fix `demo_pkg/calc.py` and watch it use `verify` + `preexisting`.
3. Create the GitHub repo, push, confirm CI is green.

## Soon (weeks 1–2 of the plan)

- pyproject: set real GitHub URLs + author email.
- LICENSE file is Apache-2.0 boilerplate — confirm and fill copyright line.
- Decide the real name (is `verdict-mcp` free on PyPI? check before attachment forms).
- First build-in-public post: "Anatomy of an MCP verification server" (outline from the scaffold).

## Parked decisions (don't reopen until v0.2)

- Coverage-based selection (grimp is the v0.1 answer)
- Flake detection (needs run volume)
- Resource limits on containers (--memory, --pids-limit)
- Non-Python adapters (community bait — write the CONTRIBUTING pitch instead)
