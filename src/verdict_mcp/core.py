"""Orchestration: the logic behind the MCP tools, kept import-friendly for tests."""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from . import gitdiff, impact
from .adapters import lint_adapters, pytest_adapter
from .config import Config
from .history import HistoryStore
from .runner import pick_runner
from .schema import Counts, Failure, FailureDetail, VerifyResult


def verdict_dir(worktree: Path) -> Path:
    return worktree / ".verdict"


def verify_core(worktree: Path, scope: str | None = None, base: str | None = None) -> VerifyResult:
    """Run impact-selected pytest checks in a sandbox; return a compact verdict."""
    t0 = time.monotonic()
    cfg = Config.load(worktree)
    store = HistoryStore(verdict_dir(worktree))
    run_id = uuid.uuid4().hex[:12]
    commit = gitdiff.head_commit(worktree)

    changed = gitdiff.changed_files(worktree, base)
    if scope == "all":
        selection = impact.Selection([], "all", "full suite requested")
    elif scope:  # explicit path
        selection = impact.Selection([scope], f"path:{scope}", None)
    else:
        selection = impact.select_tests(worktree, changed, cfg.packages)

    runner = pick_runner(cfg.prefer, image=cfg.image, setup_cmd=cfg.setup_cmd)
    outcome = runner.run(worktree, pytest_adapter.command(selection.test_paths), timeout_s=cfg.timeout_s)

    report = outcome.artifacts / pytest_adapter.REPORT_FILE
    if not report.exists():
        # pytest itself failed to run (bad env, collection error crash, missing plugin)
        return VerifyResult(
            run_id=run_id,
            ok=False,
            scope=selection.scope,
            selection_note=f"pytest did not produce a report (exit {outcome.exit_code}); "
            f"stderr tail: {outcome.stderr[-500:]!r}",
            counts=Counts(),
            failures=[],
            duration_ms=int((time.monotonic() - t0) * 1000),
            runner=outcome.runner_name,
        )

    counts_dict, failures, details = pytest_adapter.parse_report(report, changed)

    _annotate_and_record(failures, details, store, run_id, commit)

    truncated = len(failures) > cfg.max_failures
    result = VerifyResult(
        run_id=run_id,
        ok=counts_dict["failed"] == 0 and counts_dict["errors"] == 0,
        scope=selection.scope,
        selection_note=selection.note,
        counts=Counts(**counts_dict),
        failures=failures[: cfg.max_failures],
        truncated=truncated,
        duration_ms=int((time.monotonic() - t0) * 1000),
        runner=outcome.runner_name,
    )
    store.record_run(run_id, result.model_dump_json())
    return result


def run_checks_core(worktree: Path, checks: list[str] | None = None) -> VerifyResult:
    """Run lint/type checks (ruff, mypy) in the sandbox; same verdict shape."""
    t0 = time.monotonic()
    cfg = Config.load(worktree)
    store = HistoryStore(verdict_dir(worktree))
    run_id = uuid.uuid4().hex[:12]
    commit = gitdiff.head_commit(worktree)
    runner = pick_runner(cfg.prefer, image=cfg.image, setup_cmd=cfg.setup_cmd)

    checks = checks or ["ruff"]
    failures: list[Failure] = []
    runner_name = ""
    for check in checks:
        if check == "ruff":
            out = runner.run(worktree, lint_adapters.ruff_command([]), timeout_s=cfg.timeout_s)
            failures += lint_adapters.parse_ruff(out.stdout)
        elif check == "mypy":
            out = runner.run(worktree, lint_adapters.mypy_command([]), timeout_s=cfg.timeout_s)
            failures += lint_adapters.parse_mypy(out.stdout)
        else:
            continue
        runner_name = out.runner_name

    details = [
        FailureDetail(check_id=f.check_id, fingerprint=f.fingerprint, full_traceback=f.message)
        for f in failures
    ]
    _annotate_and_record(failures, details, store, run_id, commit)

    result = VerifyResult(
        run_id=run_id,
        ok=not failures,
        scope=f"checks:{','.join(checks)}",
        counts=Counts(selected=len(failures), failed=len(failures)),
        failures=failures[: cfg.max_failures],
        truncated=len(failures) > cfg.max_failures,
        duration_ms=int((time.monotonic() - t0) * 1000),
        runner=runner_name,
    )
    store.record_run(run_id, result.model_dump_json())
    return result


def _annotate_and_record(
    failures: list[Failure],
    details: list[FailureDetail],
    store: HistoryStore,
    run_id: str,
    commit: str | None,
) -> None:
    """Set `preexisting` from history *before* recording this run's failures."""
    for f in failures:
        f.preexisting = store.seen_before(f.fingerprint)
    for f in failures:
        store.record_failure(f.fingerprint, f.check_id, commit)
    for d in details:
        store.record_detail(run_id, d)
