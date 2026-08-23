import json
from pathlib import Path

from verdict_mcp.adapters.pytest_adapter import parse_report

FIXTURE = Path(__file__).parent / "fixtures" / "pytest_report.json"


def test_parse_real_report():
    counts, failures, details = parse_report(FIXTURE, diff_files=["demo_pkg/calc.py"])
    assert counts["selected"] == 4
    assert counts["passed"] == 3
    assert counts["failed"] == 1
    assert len(failures) == 1
    f = failures[0]
    assert f.check_id.startswith("pytest::")
    assert "test_divide_by_zero" in f.check_id
    assert f.fingerprint and len(f.fingerprint) == 16
    assert "ZeroDivisionError" in f.message
    assert len(details) == 1
    assert details[0].full_traceback


def test_fingerprint_stable_across_reparses():
    _, f1, _ = parse_report(FIXTURE, diff_files=[])
    _, f2, _ = parse_report(FIXTURE, diff_files=[])
    assert f1[0].fingerprint == f2[0].fingerprint


def test_report_is_actually_json():
    data = json.loads(FIXTURE.read_text())
    assert "tests" in data
