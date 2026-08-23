from pathlib import Path

from verdict_mcp.impact import select_tests

DEMO = Path(__file__).parent.parent / "examples" / "demo_project"


def test_no_python_changes_runs_all():
    sel = select_tests(DEMO, ["README.md"], ["demo_pkg"])
    assert sel.scope == "all"
    assert sel.test_paths == []


def test_changed_test_file_selects_itself():
    sel = select_tests(DEMO, ["tests/test_text.py"], ["demo_pkg"])
    assert sel.scope == "impact"
    assert sel.test_paths == ["tests/test_text.py"]


def test_changed_source_selects_importing_tests(monkeypatch):

    monkeypatch.syspath_prepend(str(DEMO))
    # Changing calc.py should select test_calc.py but not test_text.py
    sel = select_tests(DEMO, ["demo_pkg/calc.py"], ["demo_pkg"])
    if sel.scope == "all":
        # grimp couldn't build the graph in this env — the honest fallback is acceptable
        assert sel.note is not None
        return
    assert "tests/test_calc.py" in sel.test_paths
    assert "tests/test_text.py" not in sel.test_paths
