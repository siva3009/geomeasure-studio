"""
Pytest configuration and shared fixtures.
"""

import os
import sys
import pytest

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import settings

# Enforce test environment settings
settings.environment = "test"
settings.allow_in_memory_db = True
settings.db_connect_timeout = 1

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def sample_kml_path():
    """Path to sample KML test fixture."""
    return os.path.join(FIXTURES_DIR, "sample.kml")


@pytest.fixture
def invalid_file_path():
    """Path to invalid test fixture."""
    return os.path.join(FIXTURES_DIR, "invalid.txt")


@pytest.fixture
def sample_kml_bytes():
    """Raw bytes of the sample KML."""
    path = os.path.join(FIXTURES_DIR, "sample.kml")
    with open(path, "rb") as f:
        return f.read()


@pytest.fixture
def sample_shapefile_zip_path():
    """Path to sample Shapefile zip test fixture."""
    return os.path.join(FIXTURES_DIR, "sample_shapefile.zip")

