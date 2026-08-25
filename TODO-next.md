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

## v0.2 priorities (from the python-dotenv trial, 2026-08-24)

Trial: cloned python-dotenv (255 tests), two-line verdict.toml with `setup_cmd`, worked unmodified.
1. **Per-run env setup is the wall: ~2min of `pip install` on every verify.** Agents won't wait.
   Order of attack: reuse a built image layer keyed on (base image, setup_cmd, deps files hash),
   then the result cache from the build plan (tree hash + check + image digest).
2. Impact selection is coarse on hub modules (touching `variables.py` selected 184/255 — correct
   but wide). Fine for v0.1; coverage-based maps stay the v0.2 answer.
3. Selection excluded ~70 tests and said why in `selection_note` — honesty contract held.

## Distribution status (2026-08-25)

- Published `io.github.Dgotlieb/verdict-mcp` 0.1.0a4 to the official MCP Registry.
- awesome-mcp-servers PR open: https://github.com/punkpeye/awesome-mcp-servers/pull/12903
- Still to do: mcp.so / PulseMCP / Glama submission forms (Daniel, ~2 min each); Show HN Saturday ~9:30am ET.

## After the Show HN launch

- Bump `.github/workflows/substantiate.yml` pin from 06ead258 (0.1.1) to
  c6ae746b882a2454bcb8f2fa5d8587278299f8c3 (0.1.3). Deliberately deferred:
  don't change a pinned action during launch week; the 0.1.3 fixes are
  C-enum-specific and don't affect this Python repo.

## Parked decisions (don't reopen until v0.2)

- Coverage-based selection (grimp is the v0.1 answer)
- Flake detection (needs run volume)
- Resource limits on containers (--memory, --pids-limit)
- Non-Python adapters (community bait — write the CONTRIBUTING pitch instead)
