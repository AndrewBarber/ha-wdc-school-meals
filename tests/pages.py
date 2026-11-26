"""Saved council pages under tests/fixtures/ (see scripts/refresh-fixtures)."""

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def load_page(name: str) -> str:
    """Return a saved page as text."""
    return (FIXTURES / name).read_text(encoding="utf-8")
