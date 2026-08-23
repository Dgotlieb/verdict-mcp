from demo_pkg.text import shout


def test_shout():
    assert shout("hi") == "HI!"
