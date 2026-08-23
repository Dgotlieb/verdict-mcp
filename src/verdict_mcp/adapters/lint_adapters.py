"""ruff and mypy adapters — both emit machine-readable output natively.

They exist in v0.1 primarily to prove the verdict schema generalizes beyond
tests. Same Failure shape, same fingerprinting, same history.
"""

from __future__ import annotations

import json
import re

from ..fingerprint import fingerprint
from ..schema import CheckKind, Failure, Location, Status


def ruff_command(paths: list[str]) -> list[str]:
    return ["python", "-m", "ruff", "check", "--output-format", "json", *(paths or ["."])]


def parse_ruff(stdout: str) -> list[Failure]:
    try:
        items = json.loads(stdout or "[]")
    except json.JSONDecodeError:
        return []
    failures = []
    for item in items:
        code = item.get("code") or "RUFF"
        path = item.get("filename", "?")
        check_id = f"ruff::{path}::{code}"
        message = f"{code} {item.get('message', '')}".strip()
        failures.append(
            Failure(
                check_id=check_id,
                kind=CheckKind.lint,
                status=Status.failed,
                fingerprint=fingerprint(check_id, code, item.get("message", "")),
                message=message[:300],
                location=Location(file=path, line=(item.get("location") or {}).get("row")),
            )
        )
    return failures


_MYPY_LINE = re.compile(r"^(?P<file>[^:]+):(?P<line>\d+):(?:\d+:)?\s*error:\s*(?P<msg>.*?)(\s+\[(?P<code>[\w-]+)\])?$")


def mypy_command(paths: list[str]) -> list[str]:
    return ["python", "-m", "mypy", "--no-error-summary", "--show-error-codes", *(paths or ["."])]


def parse_mypy(stdout: str) -> list[Failure]:
    failures = []
    for line in stdout.splitlines():
        m = _MYPY_LINE.match(line.strip())
        if not m:
            continue
        code = m.group("code") or "mypy-error"
        check_id = f"mypy::{m.group('file')}::{code}"
        failures.append(
            Failure(
                check_id=check_id,
                kind=CheckKind.typecheck,
                status=Status.failed,
                fingerprint=fingerprint(check_id, code, m.group("msg")),
                message=f"[{code}] {m.group('msg')}"[:300],
                location=Location(file=m.group("file"), line=int(m.group("line"))),
            )
        )
    return failures
