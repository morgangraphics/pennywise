"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
import shutil
from pathlib import Path
from penny_parser import PennyParser
from penny_database import PennyDatabase


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def temp_db(temp_dir):
    """Create a temporary database for testing."""
    db_path = Path(temp_dir) / "test.db"
    db = PennyDatabase(str(db_path))
    yield db
    db.close()


@pytest.fixture
def parser(temp_dir):
    """Create a parser instance with temporary log and database files."""
    log_file = Path(temp_dir) / "test_parser.log"
    db_file = Path(temp_dir) / "test.db"
    parser = PennyParser(str(log_file), str(db_file))
    yield parser
    parser.db.close()


@pytest.fixture
def sample_penny_dict():
    """Create a sample penny dictionary for testing."""
    return {
        "State": "California",
        "City": "Anaheim",
        "Neighborhood": "Downtown Disney",
        "Location": "Downtown Disney - World of Disney",
        "Name": "Castle",
        "Orientation": "h",
        "Type": "Copper Penny",
        "Year": "2024",
        "Position": "1",
        "Retired": "",
        "Set #": "",
        "Quantity": 1,
        "Need": "",
        # Lowercase keys for database operations
        "state": "California",
        "city": "Anaheim",
        "neighborhood": "Downtown Disney",
        "location": "Downtown Disney - World of Disney",
        "name": "Castle",
        "orientation": "h",
        "type": "Copper Penny",
        "year": "2024",
        "position": "1",
    }
