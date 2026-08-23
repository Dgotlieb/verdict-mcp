from verdict_mcp.fingerprint import fingerprint, normalize


def test_normalize_collapses_addresses_and_tmp_paths():
    a = normalize("ValueError at 0xDEADBEEF in /tmp/pytest-123/file.py")
    b = normalize("ValueError at 0xCAFEBABE in /tmp/pytest-999/file.py")
    assert a == b


def test_normalize_collapses_durations_and_uuids():
    a = normalize("timeout after 3.14 seconds for job 123e4567-e89b-12d3-a456-426614174000")
    b = normalize("timeout after 9.99 seconds for job 00000000-0000-0000-0000-000000000000")
    assert a == b


def test_same_logical_failure_same_fingerprint():
    f1 = fingerprint("pytest::t.py::test_x", "AssertionError", "assert 3 == 4 at 0xAAAA")
    f2 = fingerprint("pytest::t.py::test_x", "AssertionError", "assert 3 == 4 at 0xBBBB")
    assert f1 == f2


def test_different_test_different_fingerprint():
    f1 = fingerprint("pytest::t.py::test_x", "AssertionError", "assert 3 == 4")
    f2 = fingerprint("pytest::t.py::test_y", "AssertionError", "assert 3 == 4")
    assert f1 != f2


def test_line_numbers_do_not_change_fingerprint():
    f1 = fingerprint("pytest::t.py::test_x", "TypeError", "bad call, file.py, line 10")
    f2 = fingerprint("pytest::t.py::test_x", "TypeError", "bad call, file.py, line 99")
    assert f1 == f2
