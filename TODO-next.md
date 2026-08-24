# Next session — start here

Per the build plan: never start a session without a pre-written first task.

## Immediate (session 1 on your machine)

1. ~~First real container run.~~ **Done 2026-08-23** — see `tests/test_container_runner.py` and the
   "Current state" notes in CLAUDE.md. Both configurations work: a prebuilt `image` (check run is
   `--network=none`, ~2s) and plain `python:3.12-slim` + `setup_cmd = "pip install pytest pytest-json-report"`
   (~10s). Note: `uv run` is broken on this Mac (cryptography wheels); use `.venv/bin/python -m pytest`.
2. ~~Wire into Claude Code for a dogfood run~~ **Done 2026-08-23 (scripted).** `~/demo-dogfood` has a
   `.mcp.json` + container config; the verify → break → fix loop was driven through the real stdio
   server via `fastmcp.Client` and behaves correctly (impact selects 1 test, `preexisting` flips).
   Two bugs found and fixed by dogfooding: grimp couldn't import the target project from the console
   script's venv (impact always fell back to the full suite), and `--json-report-omit` (nargs='+')
   was swallowing the test paths (every non-`all` scope ran the whole suite).
   **Still to do by hand:** open `cd ~/demo-dogfood && claude`, ask it to fix `divide()` and watch it use `verify`.
3. ~~Create the GitHub repo, push, confirm CI is green.~~ **Done.** Published `v0.1.0a1` to PyPI via trusted publishing (`release.yml` on `v*` tags).

## Soon (weeks 1–2 of the plan)

- ~~Apple Silicon Mac validation~~ done: clean install, podman rootless arm64, `uvx verdict-mcp@0.1.0a2` all green. Released 0.1.0a2.
- README: demo GIF/screenshot of the `~/demo-dogfood` session.
- First build-in-public post: "Anatomy of an MCP verification server" (outline from the scaffold).

## Parked decisions (don't reopen until v0.2)

- Coverage-based selection (grimp is the v0.1 answer)
- Flake detection (needs run volume)
- Resource limits on containers (--memory, --pids-limit)
- Non-Python adapters (community bait — write the CONTRIBUTING pitch instead)
