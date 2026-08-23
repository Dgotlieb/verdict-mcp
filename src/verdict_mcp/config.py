"""Project configuration: verdict.toml at the repo root.

Example:

    [project]
    packages = ["demo_pkg"]        # importable top-level packages (for impact selection)

    [runner]
    prefer = "podman"              # podman | docker | local
    image = "ghcr.io/you/yourproj-test:latest"
    setup_cmd = "pip install -e .[test]"   # runs WITH network; check runs get --network=none

    [limits]
    max_failures = 10              # cap the summary payload; rest behind explain_failure
    timeout_s = 600
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    packages: list[str] = field(default_factory=list)
    prefer: str | None = None
    image: str = "python:3.12-slim"
    setup_cmd: str | None = None
    max_failures: int = 10
    timeout_s: int = 600

    @classmethod
    def load(cls, worktree: Path) -> Config:
        path = worktree / "verdict.toml"
        if not path.exists():
            return cls(packages=_guess_packages(worktree))
        data = tomllib.loads(path.read_text())
        project = data.get("project", {})
        runner = data.get("runner", {})
        limits = data.get("limits", {})
        return cls(
            packages=project.get("packages") or _guess_packages(worktree),
            prefer=runner.get("prefer"),
            image=runner.get("image", "python:3.12-slim"),
            setup_cmd=runner.get("setup_cmd"),
            max_failures=int(limits.get("max_failures", 10)),
            timeout_s=int(limits.get("timeout_s", 600)),
        )


def _guess_packages(worktree: Path) -> list[str]:
    """Best-effort: top-level dirs (or src/ children) containing __init__.py."""
    candidates = []
    for base in (worktree / "src", worktree):
        if not base.is_dir():
            continue
        for child in base.iterdir():
            if child.is_dir() and (child / "__init__.py").exists() and not child.name.startswith((".", "_")):
                candidates.append(child.name)
        if candidates:
            break
    return sorted(set(candidates))
