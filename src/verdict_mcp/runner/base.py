"""Execution backends.

A Runner executes a command against a *copy or read-only view* of the
worktree and returns (exit_code, stdout, stderr, artifacts_dir). The host
worktree is never mutated by a check run.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class RunOutcome:
    exit_code: int
    stdout: str
    stderr: str
    artifacts: Path  # directory where the command was told to write report files
    runner_name: str


class Runner(Protocol):
    name: str

    def run(self, worktree: Path, command: list[str], timeout_s: int = 600) -> RunOutcome: ...
