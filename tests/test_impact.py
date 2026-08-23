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


def test_changed_source_selects_importing_tests():
    # Changing calc.py should select test_calc.py but not test_text.py
    sel = select_tests(DEMO, ["demo_pkg/calc.py"], ["demo_pkg"])
    assert sel.scope == "impact", sel.note
    assert "tests/test_calc.py" in sel.test_paths
    assert "tests/test_text.py" not in sel.test_paths


def test_impact_selection_works_for_project_outside_sys_path(tmp_path):
    """The MCP server runs as a console script: the target project is NOT importable
    from its interpreter. Impact selection must still build the graph."""
    import shutil
    import sys

    from verdict_mcp.impact import select_tests

    demo = Path(__file__).parent.parent / "examples" / "demo_project"
    repo = tmp_path / "elsewhere" / "proj"
    shutil.copytree(demo, repo)
    assert str(repo) not in sys.path

    sel = select_tests(repo, ["demo_pkg/calc.py"], ["demo_pkg"])
    assert sel.scope == "impact", sel.note
    assert sel.test_paths == ["tests/test_calc.py"]
    assert str(repo) not in sys.path  # no lasting pollution of the server's import path
