from demo_pkg.calc import add, divide


def test_add():
    assert add(2, 2) == 4


def test_add_negative():
    assert add(-1, 1) == 0


def test_divide_by_zero_is_handled():
    # Intentionally failing: demonstrates a structured verdict.
    assert divide(1, 0) == 0
