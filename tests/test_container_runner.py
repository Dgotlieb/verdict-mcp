"""ContainerRunner against a real container engine.

Tests marked `container` need a *reachable* engine (docker or podman with a
running daemon/VM); they skip otherwise. The check image is built once per
session from python:3.12-slim + pytest + pytest-json-report so the check run
itself can stay `--network=none`, which is the recommended production posture.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from verdict_mcp.runner.container import detect_engine

DEMO = Path(__file__).parent.parent / "examples" / "demo_project"
TEST_IMAGE = "verdict-test-py312:local"
DOCKERFILE = """\
FROM python:3.12-slim
RUN pip install --no-cache-dir pytest pytest-json-report
"""


@pytest.fixture(scope="session")
def engine() -> str:
    found = detect_engine()
    if not found:
        pytest.skip("no reachable container engine (docker/podman)")
    return found


@pytest.fixture(scope="session")
def test_image(engine: str) -> str:
    subprocess.run(
        [engine, "build", "-q", "-t", TEST_IMAGE, "-"],
        input=DOCKERFILE, text=True, check=True, capture_output=True,
    )
    return TEST_IMAGE


@pytest.fixture()
def demo_repo(tmp_path: Path, engine: str, test_image: str) -> Path:
    repo = tmp_path / "demo"
    shutil.copytree(DEMO, repo)
    (repo / "verdict.toml").write_text(
        f'[project]\npackages = ["demo_pkg"]\n\n[runner]\nprefer = "{engine}"\nimage = "{test_image}"\n'
    )
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
        cwd=repo, check=True,
    )
    return repo


@pytest.mark.container
def test_verify_runs_inside_container(demo_repo: Path, engine: str):
    from verdict_mcp.core import verify_core

    result = verify_core(demo_repo, scope="all")
    assert result.runner == engine
    assert result.counts.selected == 4, result.selection_note
    assert result.counts.passed == 3
    assert result.counts.failed == 1
    assert "ZeroDivisionError" in result.failures[0].message


@pytest.mark.container
def test_container_run_does_not_mutate_worktree(demo_repo: Path):
    from verdict_mcp.core import verify_core

    before = _tree_snapshot(demo_repo)
    verify_core(demo_repo, scope="all")
    assert _tree_snapshot(demo_repo) == before


def _tree_snapshot(root: Path) -> set[tuple[str, int]]:
    out = set()
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        if rel.parts[0] in (".git", ".verdict"):
            continue
        if p.is_file():
            out.add((str(rel), p.stat().st_size))
    return out


def test_detect_engine_skips_engine_whose_daemon_is_unreachable(tmp_path: Path, monkeypatch):
    """An engine binary on PATH whose `info` fails (stopped podman VM) must not be chosen."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    dead = fake_bin / "podman"
    dead.write_text("#!/bin/sh\necho 'Cannot connect to Podman' >&2\nexit 125\n")
    dead.chmod(dead.stat().st_mode | stat.S_IEXEC)
    alive = fake_bin / "docker"
    alive.write_text("#!/bin/sh\nexit 0\n")
    alive.chmod(alive.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    assert detect_engine() == "docker"
