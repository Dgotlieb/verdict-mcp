"""verdict-mcp — the MCP server surface.

Four tools, one design rule: summaries are tiny, detail is on demand.

Run:  verdict-mcp   (stdio transport; point it at a project with VERDICT_PROJECT
      or run it from the project root)
"""

from __future__ import annotations

import os
from pathlib import Path

from fastmcp import FastMCP

from .core import run_checks_core, verdict_dir, verify_core
from .history import HistoryStore

mcp = FastMCP(
    "verdict",
    instructions=(
        "Structured, sandboxed verification for this codebase. Call `verify` after making "
        "changes instead of running pytest yourself: it selects affected tests, runs them in "
        "an isolated environment, and returns compact structured failures with fingerprints. "
        "A failure with preexisting=true was broken BEFORE your change — do not try to fix it "
        "unless asked. Use `explain_failure` for full tracebacks and `history` to see how long "
        "a failure has existed."
    ),
)


def _project() -> Path:
    return Path(os.environ.get("VERDICT_PROJECT", os.getcwd())).resolve()


@mcp.tool
def verify(scope: str | None = None, base: str | None = None) -> dict:
    """Verify the current working-tree changes by running affected pytest tests in a sandbox.

    Args:
        scope: None for impact-based selection (default), 'all' for the full suite,
               or a path like 'tests/test_api.py' to run one file.
        base: git ref to diff against (default: HEAD, i.e. uncommitted changes).

    Returns a compact verdict: pass/fail counts and structured failures, each with a
    stable fingerprint and a `preexisting` flag (true = broken before this change).
    """
    return verify_core(_project(), scope=scope, base=base).model_dump(exclude_none=True)


@mcp.tool
def explain_failure(check_id: str, run_id: str | None = None) -> dict:
    """Full traceback and output for one failing check from a previous `verify` run.

    Args:
        check_id: the failure's check_id, e.g. 'pytest::tests/test_x.py::test_y'.
        run_id: optional; defaults to the most recent run containing this check.
    """
    detail = HistoryStore(verdict_dir(_project())).get_detail(check_id, run_id)
    if detail is None:
        return {"error": f"no recorded detail for {check_id!r}; run `verify` first"}
    return detail.model_dump()


@mcp.tool
def history(fingerprint: str) -> dict:
    """When was this failure fingerprint first/last seen, and how many times?

    Use this to distinguish a regression you introduced (unknown fingerprint)
    from long-standing breakage (fingerprint seen across many runs/commits).
    """
    entry = HistoryStore(verdict_dir(_project())).get_history(fingerprint)
    if entry is None:
        return {"fingerprint": fingerprint, "known": False,
                "meaning": "never seen before — if it appeared after your change, it is your regression"}
    return {"known": True, **entry.model_dump()}


@mcp.tool
def run_checks(checks: list[str] | None = None) -> dict:
    """Run lint/type checks ('ruff', 'mypy') in the sandbox; same verdict shape as `verify`."""
    return run_checks_core(_project(), checks).model_dump(exclude_none=True)


def main(argv: list[str] | None = None) -> None:
    import argparse
    from importlib.metadata import version

    parser = argparse.ArgumentParser(
        prog="verdict-mcp",
        description=(
            "MCP server (stdio) giving coding agents structured, sandboxed test feedback. "
            "Point it at a project with VERDICT_PROJECT=/path/to/repo (default: current directory)."
        ),
        epilog="Configure via verdict.toml in the project root. Docs: https://github.com/Dgotlieb/verdict-mcp",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {version('verdict-mcp')}")
    parser.parse_args(argv)
    mcp.run()


if __name__ == "__main__":
    main()
