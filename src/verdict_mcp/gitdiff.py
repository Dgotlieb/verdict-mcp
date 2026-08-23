"""Changed-file detection via git."""

from __future__ import annotations

import subprocess
from pathlib import Path


def changed_files(worktree: Path, base: str | None = None) -> list[str]:
    """Files changed vs `base` (default: uncommitted changes vs HEAD).

    Returns repo-relative paths. Includes staged, unstaged, and untracked files.
    """
    ref = base or "HEAD"
    out: set[str] = set()
    for args in (
        ["git", "diff", "--name-only", ref],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ):
        proc = subprocess.run(args, cwd=worktree, capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            out.update(line.strip() for line in proc.stdout.splitlines() if line.strip())
    return sorted(out)


def head_commit(worktree: Path) -> str | None:
    proc = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=worktree, capture_output=True, text=True, check=False
    )
    return proc.stdout.strip() if proc.returncode == 0 else None
