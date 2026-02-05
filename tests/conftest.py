"""Test configuration and fixtures for pytest."""

import pytest
from pathlib import Path


@pytest.fixture
def data_dir():
    """Return the data directory path."""
    return Path(__file__).parent.parent / "src" / "data"


@pytest.fixture
def test_data_dir(tmp_path):
    """Create a temporary data directory for tests."""
    test_dir = tmp_path / "data"
    test_dir.mkdir()
    return test_dir
