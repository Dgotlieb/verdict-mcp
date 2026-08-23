"""End-to-end: verify_core against the demo project with the local runner.

Copies the demo project into a temp git repo so history state doesn't leak
between test runs.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

DEMO = Path(__file__).parent.parent / "examples" / "demo_project"


@pytest.fixture()
def demo_repo(tmp_path):
    repo = tmp_path / "demo"
    shutil.copytree(DEMO, repo)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
        cwd=repo, check=True,
    )
    return repo


def test_verify_full_suite(demo_repo):
    from verdict_mcp.core import verify_core

    result = verify_core(demo_repo, scope="all")
    assert result.runner == "local"
    assert result.counts.selected == 4
    assert result.counts.passed == 3
    assert result.counts.failed == 1
    assert not result.ok
    f = result.failures[0]
    assert "ZeroDivisionError" in f.message
    assert f.preexisting is False  # first time seen


def test_preexisting_flag_flips_on_second_run(demo_repo):
    from verdict_mcp.core import verify_core

    first = verify_core(demo_repo, scope="all")
    assert first.failures[0].preexisting is False
    second = verify_core(demo_repo, scope="all")
    assert second.failures[0].preexisting is True  # known failure, not a new regression


def test_explain_failure_has_full_traceback(demo_repo):
    from verdict_mcp.core import verdict_dir, verify_core
    from verdict_mcp.history import HistoryStore

    result = verify_core(demo_repo, scope="all")
    check_id = result.failures[0].check_id
    detail = HistoryStore(verdict_dir(demo_repo)).get_detail(check_id, result.run_id)
    assert detail is not None
    assert "ZeroDivisionError" in detail.full_traceback


def test_history_lookup(demo_repo):
    from verdict_mcp.core import verdict_dir, verify_core
    from verdict_mcp.history import HistoryStore

    result = verify_core(demo_repo, scope="all")
    fp = result.failures[0].fingerprint
    entry = HistoryStore(verdict_dir(demo_repo)).get_history(fp)
    assert entry is not None
    assert entry.times_seen == 1


def test_summary_is_small(demo_repo):
    """The core promise: the verdict payload stays tiny."""
    from verdict_mcp.core import verify_core

    result = verify_core(demo_repo, scope="all")
    payload = result.model_dump_json(exclude_none=True)
    assert len(payload) < 4000  # chars, i.e. ~1k tokens worst case for this project


def test_server_tools_registered():
    import anyio

    from verdict_mcp.server import mcp

    tools = anyio.run(mcp.list_tools)
    names = {t.name for t in tools}
    assert {"verify", "explain_failure", "history", "run_checks"} <= names
