"""Local (non-containerized) runner.

Used for development, CI of verdict itself, and as an explicit opt-in
fallback when no container runtime exists. It still protects the worktree:
checks run against a temporary copy, never in place.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .base import TIMEOUT_EXIT, RunOutcome

_IGNORE = shutil.ignore_patterns(
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".verdict"
)


class LocalRunner:
    name = "local"

    def run(self, worktree: Path, command: list[str], timeout_s: int = 600) -> RunOutcome:
        tmp = Path(tempfile.mkdtemp(prefix="verdict-run-"))
        workdir = tmp / "work"
        artifacts = tmp / "artifacts"
        artifacts.mkdir(parents=True)
        shutil.copytree(worktree, workdir, ignore=_IGNORE, symlinks=True)

        # Container runner expands $VERDICT_ARTIFACTS via sh; do it manually here.
        command = [c.replace("$VERDICT_ARTIFACTS", str(artifacts)) for c in command]
        # Use this interpreter (the one with pytest/ruff/mypy installed), not whatever
        # bare `python` resolves to on PATH.
        if command and command[0] == "python":
            import sys

            command[0] = sys.executable

        try:
            proc = subprocess.run(
                command,
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
                env=_check_env(workdir, artifacts),
            )
        except subprocess.TimeoutExpired as exc:  # subprocess.run already killed the child
            return RunOutcome(
                exit_code=TIMEOUT_EXIT,
                stdout=_text(exc.stdout),
                stderr=_text(exc.stderr) + f"\nverdict: check timed out after {timeout_s}s",
                artifacts=artifacts,
                runner_name=self.name,
                scratch=tmp,
            )
        return RunOutcome(
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            artifacts=artifacts,
            runner_name=self.name,
            scratch=tmp,
        )


def _text(data: str | bytes | None) -> str:
    if data is None:
        return ""
    return data.decode(errors="replace") if isinstance(data, bytes) else data


def _check_env(workdir: Path, artifacts: Path) -> dict[str, str]:
    import os

    env = dict(os.environ)
    env["VERDICT_ARTIFACTS"] = str(artifacts)
    # Keep tool caches inside the sandbox copy.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env
