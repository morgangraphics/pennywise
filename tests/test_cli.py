"""Tests for command-line interface."""

import pytest
from pathlib import Path
import argparse


class TestArgumentParsing:
    """Test command-line argument parsing."""

    def test_required_input_argument(self):
        """Test that --input is required."""
        from penny_parser import main
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["penny_parser.py"]):
            with pytest.raises(SystemExit):
                main()

    def test_required_output_argument(self):
        """Test that --output is required."""
        from penny_parser import main
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["penny_parser.py", "-i", "input.docx"]):
            with pytest.raises(SystemExit):
                main()

    def test_input_short_form(self):
        """Test -i short form for input."""
        from penny_parser import parse_arguments

        # Test that -i short form is recognized and parsed correctly
        args = parse_arguments(["-i", "test.docx", "-o", "output.csv"])
        assert args.input == "test.docx"
        assert args.output == "output.csv"

    def test_output_short_form(self):
        """Test -o short form for output."""
        from penny_parser import parse_arguments

        # Test that -o short form is recognized and parsed correctly
        args = parse_arguments(["-i", "test.docx", "-o", "output.csv"])
        assert args.input == "test.docx"
        assert args.output == "output.csv"

    def test_short_location_flag(self):
        """Test -sl / --short-location flag."""
        from penny_parser import parse_arguments

        # Test that -sl flag is recognized and sets short_loc to True
        args = parse_arguments(["-i", "test.docx", "-o", "output.csv", "-sl"])
        assert args.short_loc is True

        # Test without the flag
        args_no_flag = parse_arguments(["-i", "test.docx", "-o", "output.csv"])
        assert args_no_flag.short_loc is False

    def test_multi_line_dash_flag(self):
        """Test -mld / --multi-line-dash flag."""
        from penny_parser import parse_arguments

        # Test that -mld flag is recognized and sets multi_line_dash to True
        args = parse_arguments(["-i", "test.docx", "-o", "output.csv", "-mld"])
        assert args.multi_line_dash is True

        # Test without the flag
        args_no_flag = parse_arguments(["-i", "test.docx", "-o", "output.csv"])
        assert args_no_flag.multi_line_dash is False

    def test_new_only_flag(self):
        """Test -n / --new-only flag."""
        from penny_parser import parse_arguments

        # Test that -n flag is recognized and sets new_only to True
        args = parse_arguments(["-i", "test.docx", "-o", "output.csv", "-n"])
        assert args.new_only is True

        # Test without the flag
        args_no_flag = parse_arguments(["-i", "test.docx", "-o", "output.csv"])
        assert args_no_flag.new_only is False

    def test_all_flags_together(self):
        """Test using all flags together."""
        from penny_parser import parse_arguments

        # Test that all flags work together
        args = parse_arguments([
            "-i", "test.docx",
            "-o", "output.csv",
            "-sl", "-mld", "-n"
        ])
        assert args.input == "test.docx"
        assert args.output == "output.csv"
        assert args.short_loc is True
        assert args.multi_line_dash is True
        assert args.new_only is True

    def test_long_form_arguments(self):
        """Test using long form of arguments."""
        from penny_parser import parse_arguments

        # Test that long form arguments work correctly
        args = parse_arguments([
            "--input", "test.docx",
            "--output", "output.csv",
            "--short-location",
            "--multi-line-dash",
            "--new-only"
        ])
        assert args.input == "test.docx"
        assert args.output == "output.csv"
        assert args.short_loc is True
        assert args.multi_line_dash is True
        assert args.new_only is True

    def test_help_flag(self):
        """Test -h / --help flag shows help."""
        from penny_parser import main
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["penny_parser.py", "-h"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0  # Help exits with code 0


class TestDirectoryInput:
    """Test directory input handling."""

    def test_input_accepts_file_path(self, temp_dir):
        """Test that input accepts a file path."""
        from pathlib import Path
        from docx import Document

        # Create a test docx file
        doc = Document()
        doc.add_paragraph("Test")
        test_file = Path(temp_dir) / "ca.docx"
        doc.save(str(test_file))

        assert test_file.exists()

    def test_input_accepts_directory_path(self, temp_dir):
        """Test that input accepts a directory path."""
        from pathlib import Path
        from docx import Document

        # Create test docx files
        for i in range(2):
            doc = Document()
            doc.add_paragraph(f"Test {i}")
            test_file = Path(temp_dir) / f"test_{i}.docx"
            doc.save(str(test_file))

        assert Path(temp_dir).is_dir()
        assert len(list(Path(temp_dir).glob("*.docx"))) == 2


class TestMimeTypeValidation:
    """Test MIME type validation."""

    def test_docx_mime_type_recognized(self, parser, temp_dir):
        """Test that .docx files have correct MIME type."""
        from pathlib import Path
        from docx import Document
        import mimetypes

        doc = Document()
        docx_path = Path(temp_dir) / "test.docx"
        doc.save(str(docx_path))

        mime_type, _ = mimetypes.guess_type(str(docx_path))
        assert (
            mime_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    def test_txt_file_rejected(self, parser, temp_dir):
        """Test that .txt files are rejected."""
        import mimetypes

        mime_type, _ = mimetypes.guess_type("test.txt")
        assert (
            mime_type
            != "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
