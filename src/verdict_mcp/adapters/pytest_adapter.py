"""pytest adapter: run pytest with pytest-json-report, parse into verdicts."""

from __future__ import annotations

import json
from pathlib import Path

from ..fingerprint import fingerprint
from ..schema import CheckKind, Failure, FailureDetail, Location, Status

REPORT_FILE = "verdict-pytest-report.json"


def command(test_paths: list[str]) -> list[str]:
    """The pytest invocation. Report goes to the artifacts dir via env var expansion in sh."""
    base = [
        "python", "-m", "pytest",
        "-q", "-p", "no:cacheprovider",
        "--json-report", f"--json-report-file=$VERDICT_ARTIFACTS/{REPORT_FILE}",
        "--json-report-omit", "collectors", "warnings",
    ]
    return base + test_paths


def command_local(test_paths: list[str], artifacts: Path) -> list[str]:
    """Variant with a concrete artifacts path (no shell expansion in local runner)."""
    base = [
        "python", "-m", "pytest",
        "-q", "-p", "no:cacheprovider",
        "--json-report", f"--json-report-file={artifacts / REPORT_FILE}",
        "--json-report-omit", "collectors", "warnings",
    ]
    return base + test_paths


_OUTCOME_MAP = {
    "passed": Status.passed,
    "failed": Status.failed,
    "error": Status.error,
    "skipped": Status.skipped,
    "xfailed": Status.passed,   # expected failure = not actionable
    "xpassed": Status.failed,   # unexpectedly passing xfail IS actionable
}


def parse_report(report_path: Path, diff_files: list[str]) -> tuple[dict, list[Failure], list[FailureDetail]]:
    """Returns (counts_dict, failures, details)."""
    data = json.loads(report_path.read_text())
    counts = {"selected": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    failures: list[Failure] = []
    details: list[FailureDetail] = []

    for test in data.get("tests", []):
        counts["selected"] += 1
        status = _OUTCOME_MAP.get(test.get("outcome", ""), Status.error)
        if status is Status.passed:
            counts["passed"] += 1
            continue
        if status is Status.skipped:
            counts["skipped"] += 1
            continue
        counts["failed" if status is Status.failed else "errors"] += 1

        check_id = f"pytest::{test.get('nodeid', '?')}"
        stage = _failing_stage(test)
        crash = (stage or {}).get("crash") or {}
        message = crash.get("message") or (stage or {}).get("longrepr", "")[:400] or "unknown failure"
        error_type = message.split(":", 1)[0][:120]
        fp = fingerprint(check_id, error_type, message)

        expected, actual = _parse_assertion(message)
        stack_slice = _diff_frames(stage, diff_files)
        loc = None
        if crash.get("path"):
            loc = Location(file=str(crash["path"]), line=crash.get("lineno"))

        failures.append(
            Failure(
                check_id=check_id,
                kind=CheckKind.test,
                status=status,
                fingerprint=fp,
                message=message.splitlines()[0][:300],
                assertion=_first_assert_line(stage),
                expected=expected,
                actual=actual,
                location=loc,
                stack_slice=stack_slice,
            )
        )
        details.append(
            FailureDetail(
                check_id=check_id,
                fingerprint=fp,
                full_traceback=(stage or {}).get("longrepr", "") or message,
            )
        )
    return counts, failures, details


def _failing_stage(test: dict) -> dict | None:
    for stage_name in ("call", "setup", "teardown"):
        stage = test.get(stage_name)
        if stage and stage.get("outcome") in ("failed", "error"):
            return stage
    return test.get("call") or test.get("setup")


def _parse_assertion(message: str) -> tuple[str | None, str | None]:
    """Best-effort expected/actual extraction from 'assert X == Y' style messages."""
    for line in message.splitlines():
        line = line.strip()
        if line.startswith("assert ") and " == " in line:
            lhs, rhs = line[len("assert "):].split(" == ", 1)
            return rhs.strip(), lhs.strip()
    return None, None


def _first_assert_line(stage: dict | None) -> str | None:
    longrepr = (stage or {}).get("longrepr") or ""
    for line in longrepr.splitlines():
        stripped = line.strip().lstrip("> ")
        if stripped.startswith("assert "):
            return stripped[:200]
    return None


def _diff_frames(stage: dict | None, diff_files: list[str]) -> list[str]:
    """Traceback frames whose file appears in the diff — the frames the agent caused."""
    frames = (stage or {}).get("traceback") or []
    diff_set = set(diff_files)
    out = []
    for frame in frames:
        path = str(frame.get("path", ""))
        if path in diff_set or any(path.endswith(d) or d.endswith(path) for d in diff_set):
            out.append(f"{path}:{frame.get('lineno')} {frame.get('message', '')}".strip())
    return out[:5]
