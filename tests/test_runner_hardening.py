"""Runner robustness: honest fallback, timeouts, and temp-dir hygiene."""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
from pathlib import Path

import pytest

from verdict_mcp.runner import LocalRunner
from verdict_mcp.runner.container import ContainerRunner, choose_runner, detect_engine


def _fake_engine(bin_dir: Path, name: str, script: str) -> None:
    p = bin_dir / name
    p.write_text("#!/bin/sh\n" + script)
    p.chmod(p.stat().st_mode | stat.S_IEXEC)


@pytest.fixture()
def dead_docker_on_path(tmp_path: Path, monkeypatch) -> Path:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _fake_engine(fake_bin, "docker", "echo 'Cannot connect to the Docker daemon' >&2\nexit 1\n")
    _fake_engine(fake_bin, "podman", "exit 125\n")
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")
    return fake_bin


def test_preferred_engine_unreachable_falls_back_with_a_note(dead_docker_on_path):
    runner, note = choose_runner("docker")
    assert runner.name == "local"
    assert note is not None
    assert "docker" in note and "local" in note


def test_explicit_local_preference_has_no_note():
    runner, note = choose_runner("local")
    assert runner.name == "local"
    assert note is None


def test_verify_result_carries_runner_note(dead_docker_on_path, tmp_path):
    from verdict_mcp.core import verify_core

    repo = _demo_repo(tmp_path, 'prefer = "docker"')
    result = verify_core(repo, scope="all")
    assert result.runner == "local"
    assert result.runner_note and "docker" in result.runner_note


def test_local_runner_timeout_returns_outcome_not_exception(tmp_path):
    out = LocalRunner().run(tmp_path, ["python", "-c", "import time; time.sleep(30)"], timeout_s=1)
    assert out.exit_code == 124
    assert "timed out" in out.stderr


@pytest.mark.container
def test_container_timeout_kills_container():
    engine = detect_engine()
    if not engine:
        pytest.skip("no reachable container engine")
    runner = ContainerRunner(engine, image="python:3.12-slim")
    src = Path(tempfile.mkdtemp(prefix="verdict-src-"))
    out = runner.run(src, ["sleep", "60"], timeout_s=3)
    assert out.exit_code == 124
    assert "timed out" in out.stderr
    ps = subprocess.run(
        [engine, "ps", "--filter", "name=verdict-", "-q"], capture_output=True, text=True, check=True
    )
    assert ps.stdout.strip() == "", f"container still running: {ps.stdout}"


def test_verify_cleans_up_run_temp_dirs(tmp_path):
    from verdict_mcp.core import verify_core

    repo = _demo_repo(tmp_path, 'prefer = "local"')
    before = _verdict_tmp_dirs()
    verify_core(repo, scope="all")
    assert _verdict_tmp_dirs() - before == set()


def _verdict_tmp_dirs() -> set[str]:
    root = Path(tempfile.gettempdir())
    return {p.name for p in root.iterdir() if p.name.startswith(("verdict-run-", "verdict-artifacts-"))}


def _demo_repo(tmp_path: Path, runner_line: str) -> Path:
    import shutil

    demo = Path(__file__).parent.parent / "examples" / "demo_project"
    repo = tmp_path / "demo"
    shutil.copytree(demo, repo)
    (repo / "verdict.toml").write_text(f'[project]\npackages = ["demo_pkg"]\n\n[runner]\n{runner_line}\n')
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
        cwd=repo, check=True,
    )
    return repo


@pytest.fixture()
def engine_that_cannot_start_images(tmp_path: Path, monkeypatch) -> Path:
    """`info` works, `run` fails like a registry/auth problem would (exit 125)."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _fake_engine(
        fake_bin, "docker",
        'case "$1" in info) exit 0;; kill) exit 0;; esac\n'
        "echo 'Error: initializing source docker://python:3.12-slim: unauthorized' >&2\nexit 125\n",
    )
    _fake_engine(fake_bin, "podman", "exit 125\n")
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")
    return fake_bin


def test_verify_explains_when_container_cannot_start(engine_that_cannot_start_images, tmp_path):
    from verdict_mcp.core import verify_core

    repo = _demo_repo(tmp_path, 'prefer = "docker"')
    result = verify_core(repo, scope="all")
    assert not result.ok
    assert result.counts.selected == 0
    note = result.selection_note or ""
    assert "container" in note and "docker" in note and "unauthorized" in note
