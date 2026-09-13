"""Bootstrap package tests."""

from mercadona_mcp import __version__


def test_package_has_a_version() -> None:
    assert __version__ == "0.0.0"
