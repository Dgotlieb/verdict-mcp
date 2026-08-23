"""Execution backends.

A Runner executes a command against a *copy or read-only view* of the
worktree and returns (exit_code, stdout, stderr, artifacts_dir). The host
worktree is never mutated by a check run.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

TIMEOUT_EXIT = 124  # same convention as coreutils `timeout`


@dataclass
class RunOutcome:
    exit_code: int
    stdout: str
    stderr: str
    artifacts: Path  # directory where the command was told to write report files
    runner_name: str
    scratch: Path | None = None  # extra temp root to remove on cleanup (e.g. local work copy)

    def cleanup(self) -> None:
        """Remove temp dirs created for this run. Safe to call more than once."""
        for d in (self.scratch, self.artifacts):
            if d is not None:
                shutil.rmtree(d, ignore_errors=True)


class Runner(Protocol):
    name: str

    def run(self, worktree: Path, command: list[str], timeout_s: int = 600) -> RunOutcome: ...
