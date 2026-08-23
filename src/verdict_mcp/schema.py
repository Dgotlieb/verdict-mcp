"""Typed verdict schema — the core contract of verdict-mcp.

Design rule: the *summary* payload an agent receives must stay small
(hundreds of tokens, not tens of thousands). Anything bulky lives behind
`explain_failure(check_id)`.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

SCHEMA_VERSION = "0.1"


class CheckKind(str, Enum):
    test = "test"
    lint = "lint"
    typecheck = "typecheck"


class Status(str, Enum):
    passed = "passed"
    failed = "failed"
    error = "error"
    skipped = "skipped"


class Location(BaseModel):
    file: str
    line: int | None = None


class Failure(BaseModel):
    """One failing check, compressed to what an agent needs to act."""

    check_id: str = Field(description="Stable id, e.g. 'pytest::tests/test_x.py::test_y'")
    kind: CheckKind
    status: Status
    fingerprint: str = Field(description="Stable hash of the normalized failure signature")
    preexisting: bool | None = Field(
        default=None,
        description="True if this exact fingerprint was seen before the current diff — "
        "i.e. NOT a regression introduced by the change under verification.",
    )
    message: str = Field(description="Normalized one-line failure message")
    assertion: str | None = Field(default=None, description="Failing assertion expression, if extractable")
    expected: str | None = None
    actual: str | None = None
    location: Location | None = None
    stack_slice: list[str] = Field(
        default_factory=list,
        description="Only the traceback frames that intersect the files in the current diff",
    )


class Counts(BaseModel):
    selected: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0


class VerifyResult(BaseModel):
    """The summary verdict returned by `verify`. Keep it tiny."""

    schema_version: str = SCHEMA_VERSION
    run_id: str
    ok: bool
    scope: str = Field(description="How checks were selected: 'impact', 'all', or an explicit path")
    selection_note: str | None = Field(
        default=None, description="Honesty field: e.g. 'import-graph selection is approximate'"
    )
    counts: Counts
    failures: list[Failure] = Field(default_factory=list)
    truncated: bool = Field(
        default=False, description="True if failures were capped; use explain_failure/history for more"
    )
    duration_ms: int = 0
    runner: str = Field(default="", description="Execution backend, e.g. 'podman', 'docker', 'local'")
    runner_note: str | None = Field(
        default=None, description="Honesty field: set when checks ran somewhere other than configured"
    )


class FailureDetail(BaseModel):
    """Full detail for one failure — returned only on demand."""

    check_id: str
    fingerprint: str
    full_traceback: str
    stdout_tail: str | None = None
    stderr_tail: str | None = None


class HistoryEntry(BaseModel):
    fingerprint: str
    check_id: str
    first_seen: str
    last_seen: str
    times_seen: int
    first_seen_commit: str | None = None
