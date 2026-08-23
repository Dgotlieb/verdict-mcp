"""Containerized runner: podman preferred, docker fallback.

v0.1 posture (documented in SECURITY.md):
- worktree mounted read-only at /src
- copied to a writable /work inside the container before the check runs
- --network=none for check runs (setup_cmd, if configured, runs with network)
- default image is plain python:3.12-slim; projects with dependencies should
  set `image` (a prebuilt env) and/or `setup_cmd` in verdict.toml
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .base import RunOutcome

DEFAULT_IMAGE = "python:3.12-slim"
ARTIFACTS_MOUNT = "/artifacts"


def engine_available(engine: str) -> bool:
    """True if `engine` is on PATH *and* its daemon/VM answers (`<engine> info`).

    A podman binary with a stopped VM, or a docker client with no daemon, is
    on PATH but useless; picking it would fail every run.
    """
    if not shutil.which(engine):
        return False
    try:
        proc = subprocess.run(
            [engine, "info"], capture_output=True, text=True, timeout=15, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def detect_engine() -> str | None:
    for engine in ("podman", "docker"):
        if engine_available(engine):
            return engine
    return None


class ContainerRunner:
    def __init__(self, engine: str, image: str = DEFAULT_IMAGE, setup_cmd: str | None = None):
        self.engine = engine
        self.image = image
        self.setup_cmd = setup_cmd
        self.name = engine

    def run(self, worktree: Path, command: list[str], timeout_s: int = 600) -> RunOutcome:
        artifacts = Path(tempfile.mkdtemp(prefix="verdict-artifacts-"))
        # Args are shell-quoted below, so `$VERDICT_ARTIFACTS` would never expand;
        # resolve it to the in-container mount path here (LocalRunner does the same).
        command = [c.replace("$VERDICT_ARTIFACTS", ARTIFACTS_MOUNT) for c in command]
        inner = "set -e; cp -r /src /work; cd /work; "
        if self.setup_cmd:
            inner += f"{self.setup_cmd}; "
        inner += " ".join(_shquote(c) for c in command)

        args = [
            self.engine, "run", "--rm",
            "-v", f"{worktree}:/src:ro",
            "-v", f"{artifacts}:{ARTIFACTS_MOUNT}",
            "-e", f"VERDICT_ARTIFACTS={ARTIFACTS_MOUNT}",
            "-w", "/",
        ]
        if not self.setup_cmd:
            args += ["--network", "none"]
        args += [self.image, "sh", "-c", inner]

        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout_s, check=False)
        return RunOutcome(
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            artifacts=artifacts,
            runner_name=self.name,
        )


def _shquote(s: str) -> str:
    import shlex

    return shlex.quote(s)


def pick_runner(prefer: str | None = None, image: str = DEFAULT_IMAGE, setup_cmd: str | None = None):
    """Return the best available runner. `prefer='local'` forces the local fallback."""
    from .local import LocalRunner

    if prefer == "local":
        return LocalRunner()
    if prefer in ("podman", "docker") and engine_available(prefer):
        return ContainerRunner(prefer, image=image, setup_cmd=setup_cmd)
    engine = detect_engine()
    if engine:
        return ContainerRunner(engine, image=image, setup_cmd=setup_cmd)
    return LocalRunner()
