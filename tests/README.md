# Pennywise Test Suite

Comprehensive test suite for the pennywise project using pytest.

## Running Tests

### Install pytest and dependencies

```bash
pip install pytest python-docx
```

### Run all tests

```bash
pytest tests/
```

### Run specific test file

```bash
pytest tests/test_parser_text_methods.py
```

### Run specific test class

```bash
pytest tests/test_parser_city_location.py::TestDetectCityLocationNeighborhood
```

### Run specific test

```bash
pytest tests/test_parser_city_location.py::TestDetectCityLocationNeighborhood::test_two_lines_no_dash
```

### Run with verbose output

```bash
pytest tests/ -v
```

### Run with coverage

```bash
pip install pytest-cov
pytest tests/ --cov=. --cov-report=html
```

## Test Organization

### `conftest.py`
Shared pytest fixtures used across test suite:
- `temp_dir`: Temporary directory for test files
- `temp_db`: Temporary SQLite database instance
- `parser`: PennyParser instance with temporary log/db files
- `sample_penny_dict`: Sample penny dictionary for testing

### `test_parser_text_methods.py`
Tests for text parsing and sanitization:
- `TestSplitAndStrip`: Splitting text on delimiters
- `TestSanitizeForCsv`: Unicode character sanitization
- `TestStripNewlines`: Newline/carriage return removal
- `TestNormalizeCellText`: Cell text normalization

### `test_parser_city_location.py`
Tests for city/location/neighborhood detection:
- `TestDetectCityLocationNeighborhood`: Label parsing logic
- Tests valid/invalid label formats
- Tests short_location flag behavior
- Tests unicode handling

### `test_parser_orientation.py`
Tests for orientation and type detection:
- `TestDetectOrientationAndType`: Penny orientation (h/v) parsing
- Tests single and multi-line names
- Tests multi_line_dash flag behavior
- Tests type string extraction

### `test_parser_state_retired.py`
Tests for state parsing and retired detection:
- `TestParseStateFromFilename`: State name lookup from filename
- Tests all US state abbreviations
- `TestCellIsRetired`: Cell shading color detection
- Tests f2dbdb (retired) and other colors

### `test_database.py`
Tests for PennyDatabase class:
- `TestPennyDatabaseInit`: Database initialization
- `TestHashPenny`: Penny hashing/uniqueness
- `TestAddAndCheckPenny`: Adding and retrieving pennies
- `TestGetPennies`: Querying database
- `TestDatabaseContextManager`: Context manager functionality

### `test_integration_ca_docx.py`
Integration tests using the actual ca.docx file:
- `TestParsingCaDocx`: Full document parsing
- Tests all flags (short_location, multi_line_dash, new_only)
- Tests output CSV generation
- `TestH2H3MapBuilder`: Heading hierarchy detection
- `TestRowsFromVerticalPairs`: Table cell pairing logic

### `test_cli.py`
Command-line interface tests:
- `TestArgumentParsing`: Argument validation
- Tests all command-line flags
- `TestDirectoryInput`: File vs directory input handling
- `TestMimeTypeValidation`: MIME type checking

## Test Coverage

The test suite covers:

✅ **Text Processing**
- Unicode sanitization (smart quotes, dashes, symbols)
- Whitespace handling
- Delimiter splitting
- Newline/carriage return removal

✅ **Label Parsing**
- Single and multi-line labels
- Neighborhood/Location detection
- Location short form vs full form
- Dash separators (hyphen and en-dash)
- Continuation words (And, Of, &)

✅ **Orientation Detection**
- Horizontal (h) and vertical (v) parsing
- Multi-line name handling
- Uppercase/lowercase normalization
- Type string extraction

✅ **State and Retirement**
- State lookup from filename
- All 50 US states
- Retired cell detection via color
- Case-insensitive hex color matching

✅ **Database Operations**
- Penny hashing/uniqueness
- Add/retrieve operations
- Query by state, year, and date
- Duplicate detection
- Context manager

✅ **Integration**
- Full document parsing (ca.docx)
- CSV output generation
- Flag combinations
- All heading levels (H1-H4)
- Table structure (vertical pairs)

✅ **CLI**
- Argument parsing
- Required arguments
- Optional flags
- Long and short forms
- File vs directory input
- MIME type validation

## Key Test Scenarios

### Valid Scenarios
- Single and multi-line labels
- Neighborhood with/without locations
- Horizontal and vertical orientation
- Retired and active pennies
- Multiple files in directory
- All US state abbreviations

### Error Handling
- Missing required files
- Invalid MIME types
- Duplicate pennies
- Invalid orientation markers
- Empty cells and documents
- Missing database
- Non-existent state abbreviations

### Edge Cases
- Unicode characters in all fields
- Extra parentheses in labels
- Multiple dashes in single line
- Mixed case state abbreviations
- Empty database queries
- Context manager closing

## Mocking and Fixtures

Tests use:
- **Pytest fixtures** for setup/teardown
- **Temporary directories** for file isolation
- **Mock objects** for CLI testing
- **Real ca.docx file** for integration tests (skipped if not found)
- **Temporary SQLite databases** for DB testing

## Running with Make

```bash
# Add to Makefile if not present
make test
```
