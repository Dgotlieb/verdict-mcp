"""Console-script niceties: `verdict-mcp --help` / `--version` must not start the server."""

import subprocess
import sys


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "verdict_mcp.server", *args],
        capture_output=True, text=True, timeout=30, check=False,
    )


def test_version_flag_prints_version_and_exits():
    from importlib.metadata import version

    proc = _run("--version")
    assert proc.returncode == 0
    assert version("verdict-mcp") in proc.stdout


def test_help_flag_prints_usage_and_exits():
    proc = _run("--help")
    assert proc.returncode == 0
    assert "VERDICT_PROJECT" in proc.stdout
    assert "Starting MCP server" not in proc.stderr
