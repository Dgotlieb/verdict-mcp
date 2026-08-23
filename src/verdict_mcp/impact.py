"""Impact-based test selection via the import graph (grimp).

v0.1 approach — deterministic and honest about being approximate:
changed .py files -> their modules -> all upstream dependents (modules that
import them, transitively) -> the test modules among those, plus test files
changed directly. If the graph can't be built, fall back to running all
tests and say so in `selection_note`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SELECTION_NOTE = (
    "impact selection uses the static import graph (approximate: dynamic imports, "
    "fixtures-by-name, and data-driven tests may be missed); pass scope='all' to run everything"
)


@dataclass
class Selection:
    test_paths: list[str]  # repo-relative test files/dirs to pass to pytest ([] => all)
    scope: str  # 'impact' | 'all'
    note: str | None


def _module_name(path: str, package_roots: list[str]) -> str | None:
    p = Path(path)
    if p.suffix != ".py":
        return None
    parts = list(p.with_suffix("").parts)
    if parts and parts[0] in package_roots:
        if parts[0] == "src":
            parts = parts[1:]
        if not parts:
            return None
        if parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)
    return ".".join(parts[1:] if parts[0] == "src" else parts).removesuffix(".__init__") or None


def select_tests(worktree: Path, changed: list[str], packages: list[str]) -> Selection:
    changed_py = [c for c in changed if c.endswith(".py")]
    if not changed_py:
        return Selection([], "all", "no python changes detected; running full suite")

    directly_changed_tests = [c for c in changed_py if _is_test_path(c)]
    changed_src = [c for c in changed_py if not _is_test_path(c)]

    if not changed_src:
        return Selection(sorted(directly_changed_tests), "impact", SELECTION_NOTE)

    try:
        import grimp

        graph = grimp.build_graph(*packages, include_external_packages=False)
    except Exception as exc:  # noqa: BLE001 — any graph failure must degrade, not crash
        return Selection([], "all", f"import graph unavailable ({type(exc).__name__}); running full suite")

    roots = ["src", *packages]
    affected_modules: set[str] = set()
    for path in changed_src:
        mod = _module_name(path, roots)
        if not mod or mod not in graph.modules:
            # unknown module (e.g. script outside packages) -> can't bound impact
            return Selection([], "all", f"changed file {path} outside known packages; running full suite")
        affected_modules.add(mod)
        affected_modules |= graph.find_upstream_modules(mod)

    test_files = _find_test_files(worktree)
    selected = set(directly_changed_tests)
    for tf in test_files:
        imported = _test_file_imports(worktree / tf)
        if imported & _expand(affected_modules):
            selected.add(tf)

    if not selected:
        return Selection([], "all", "no affected tests found via import graph; running full suite as a safety net")
    return Selection(sorted(selected), "impact", SELECTION_NOTE)


def _is_test_path(path: str) -> bool:
    p = Path(path)
    return p.name.startswith("test_") or p.name.endswith("_test.py") or "tests" in p.parts


def _find_test_files(worktree: Path) -> list[str]:
    out = []
    for p in worktree.rglob("test_*.py"):
        rel = p.relative_to(worktree)
        if any(part in {".venv", "venv", "node_modules", ".git", ".verdict"} for part in rel.parts):
            continue
        out.append(str(rel))
    return out


def _test_file_imports(path: Path) -> set[str]:
    """Top-level module names imported by a test file (AST-based, no execution)."""
    import ast

    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return set()
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    return mods


def _expand(modules: set[str]) -> set[str]:
    """{'pkg.sub.mod'} -> {'pkg', 'pkg.sub', 'pkg.sub.mod'} so prefix imports match."""
    out: set[str] = set()
    for m in modules:
        parts = m.split(".")
        for i in range(1, len(parts) + 1):
            out.add(".".join(parts[:i]))
    return out
