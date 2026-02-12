"""Tests for PennyParser class - state parsing and retired detection."""

import pytest
from pathlib import Path
from docx import Document
from docx.shared import RGBColor
from docx.oxml.ns import qn


class TestParseStateFromFilename:
    """Test the parse_state_from_filename method."""

    def test_parse_california(self, parser):
        """Test parsing California state."""
        result = parser.parse_state_from_filename("ca.docx")
        assert result == "California"

    def test_parse_colorado(self, parser):
        """Test parsing Colorado state."""
        result = parser.parse_state_from_filename("co.docx")
        assert result == "Colorado"

    def test_parse_new_york(self, parser):
        """Test parsing New York state."""
        result = parser.parse_state_from_filename("ny.docx")
        assert result == "New York"

    def test_parse_uppercase(self, parser):
        """Test that uppercase filenames are handled."""
        result = parser.parse_state_from_filename("CA.docx")
        assert result == "California"

    def test_parse_mixed_case(self, parser):
        """Test mixed case filenames."""
        result = parser.parse_state_from_filename("Ca.docx")
        assert result == "California"

    def test_parse_path_with_directory(self, parser):
        """Test parsing filename from full path."""
        result = parser.parse_state_from_filename("/path/to/ca.docx")
        assert result == "California"

    def test_parse_windows_path(self, parser):
        """Test parsing filename from Windows path."""
        result = parser.parse_state_from_filename("C:/Users/Documents/ca.docx")
        assert result == "California"

    def test_parse_unknown_state(self, parser):
        """Test parsing unknown state returns capitalized version."""
        result = parser.parse_state_from_filename("xx.docx")
        assert result == "Xx"

    def test_all_us_states(self, parser):
        """Test that all US states in state_map are parsed correctly."""
        states = [
            ("al", "Alabama"),
            ("ak", "Alaska"),
            ("az", "Arizona"),
            ("ar", "Arkansas"),
            ("ca", "California"),
            ("co", "Colorado"),
            ("ct", "Connecticut"),
            ("dc", "District of Columbia"),
            ("fl", "Florida"),
            ("ga", "Georgia"),
            ("hi", "Hawaii"),
            ("il", "Illinois"),
            ("ny", "New York"),
            ("tx", "Texas"),
            ("wa", "Washington"),
            ("wy", "Wyoming"),
        ]
        for abbrev, full_name in states:
            result = parser.parse_state_from_filename(f"{abbrev}.docx")
            assert result == full_name, f"Failed for {abbrev}"


class TestCellIsRetired:
    """Test the cell_is_retired method."""

    def test_retired_cell_f2dbdb_color(self, parser, temp_dir):
        """Test detection of retired cell with f2dbdb color."""
        from docx import Document
        from docx.oxml import OxmlElement

        doc = Document()
        table = doc.add_table(rows=1, cols=1)
        cell = table.rows[0].cells[0]
        cell.text = "Test"

        # Set the cell shading to f2dbdb
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), "f2dbdb")
        tcPr.append(shd)

        docx_path = Path(temp_dir) / "test_retired.docx"
        doc.save(str(docx_path))

        doc = Document(str(docx_path))
        cell = doc.tables[0].rows[0].cells[0]
        assert parser.cell_is_retired(cell) is True

    def test_active_cell_no_shading(self, parser, temp_dir):
        """Test that active cell without shading is not retired."""
        doc = Document()
        table = doc.add_table(rows=1, cols=1)
        cell = table.rows[0].cells[0]
        cell.text = "Test"

        docx_path = Path(temp_dir) / "test_active.docx"
        doc.save(str(docx_path))

        doc = Document(str(docx_path))
        cell = doc.tables[0].rows[0].cells[0]
        assert parser.cell_is_retired(cell) is False

    def test_active_cell_different_color(self, parser, temp_dir):
        """Test that active cell with non-retired color is not retired."""
        from docx import Document
        from docx.oxml import OxmlElement

        doc = Document()
        table = doc.add_table(rows=1, cols=1)
        cell = table.rows[0].cells[0]
        cell.text = "Test"

        # Set a different color
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), "FFFFFF")  # White
        tcPr.append(shd)

        docx_path = Path(temp_dir) / "test_white.docx"
        doc.save(str(docx_path))

        doc = Document(str(docx_path))
        cell = doc.tables[0].rows[0].cells[0]
        assert parser.cell_is_retired(cell) is False

    def test_retired_uppercase_hex_color(self, parser, temp_dir):
        """Test that uppercase hex colors are recognized."""
        from docx import Document
        from docx.oxml import OxmlElement

        doc = Document()
        table = doc.add_table(rows=1, cols=1)
        cell = table.rows[0].cells[0]
        cell.text = "Test"

        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), "F2DBDB")  # Uppercase
        tcPr.append(shd)

        docx_path = Path(temp_dir) / "test_retired_uppercase.docx"
        doc.save(str(docx_path))

        doc = Document(str(docx_path))
        cell = doc.tables[0].rows[0].cells[0]
        assert parser.cell_is_retired(cell) is True
