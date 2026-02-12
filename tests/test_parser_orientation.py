"""Tests for PennyParser class - orientation and type detection."""


class TestDetectOrientationAndType:
    """Test the detect_orientation_and_type method."""

    def test_single_line_horizontal_orientation(self, parser):
        """Test single-line label with horizontal (h) orientation."""
        label_text = "Castle View (h) Copper Penny"
        orientation, type_str, name_str = parser.detect_orientation_and_type(label_text)
        assert orientation == "h"
        assert type_str == "Copper Penny"
        assert name_str == "Castle View"

    def test_single_line_vertical_orientation(self, parser):
        """Test single-line label with vertical (v) orientation."""
        label_text = "Castle View (v) Zinc Penny"
        orientation, type_str, name_str = parser.detect_orientation_and_type(label_text)
        assert orientation == "v"
        assert type_str == "Zinc Penny"
        assert name_str == "Castle View"

    def test_uppercase_orientation(self, parser):
        """Test that uppercase orientation is normalized to lowercase."""
        label_text = "Castle View (H) Copper Penny"
        orientation, type_str, name_str = parser.detect_orientation_and_type(label_text)
        assert orientation == "h"

    def test_no_orientation(self, parser):
        """Test label without orientation marker."""
        label_text = "Castle View Copper Penny"
        orientation, type_str, name_str = parser.detect_orientation_and_type(label_text)
        assert orientation == ""
        assert type_str == ""
        assert name_str == label_text

    def test_multiline_name_with_multi_line_dash_flag(self, parser):
        """Test multi-line name with multi_line_dash flag enabled."""
        parser.multi_line_dash = True
        label_text = "Castle View\nDisney Show (h) Copper Penny"
        orientation, type_str, name_str = parser.detect_orientation_and_type(label_text)
        assert orientation == "h"
        assert type_str == "Copper Penny"
        # With multi_line_dash, intermediate lines are joined with dash
        assert "Castle View" in name_str or "Disney Show" in name_str
        parser.multi_line_dash = False

    def test_multiline_name_without_multi_line_dash_flag(self, parser):
        """Test multi-line name with multi_line_dash flag disabled."""
        parser.multi_line_dash = False
        label_text = "Castle View\nDisney Show (h) Copper Penny"
        orientation, type_str, name_str = parser.detect_orientation_and_type(label_text)
        assert orientation == "h"
        assert type_str == "Copper Penny"
        # Without multi_line_dash, lines are joined with spaces
        assert name_str is not None
        assert "\n" not in name_str
        parser.multi_line_dash = False

    def test_three_line_name(self, parser):
        """Test three-line name with orientation."""
        parser.multi_line_dash = True
        label_text = "Line One\nLine Two\nLine Three (h) Copper Penny"
        orientation, type_str, name_str = parser.detect_orientation_and_type(label_text)
        assert orientation == "h"
        assert type_str == "Copper Penny"
        assert "Line One" in name_str
        assert "Line Two" in name_str
        parser.multi_line_dash = False

    def test_type_with_multiple_words(self, parser):
        """Test type string with multiple words."""
        label_text = "Castle View (h) Special Edition Copper Penny"
        orientation, type_str, name_str = parser.detect_orientation_and_type(label_text)
        assert orientation == "h"
        assert type_str == "Special Edition Copper Penny"

    def test_name_with_parentheses(self, parser):
        """Test name containing other parentheses besides orientation."""
        label_text = "Castle View (The Main One) (h) Copper Penny"
        orientation, type_str, name_str = parser.detect_orientation_and_type(label_text)
        assert orientation == "h"
        assert type_str == "Copper Penny"
        assert "Castle View" in name_str
        # First set of parentheses should be preserved in name
        assert "(The Main One)" in name_str

    def test_empty_label(self, parser):
        """Test empty label."""
        label_text = ""
        orientation, type_str, name_str = parser.detect_orientation_and_type(label_text)
        assert orientation == ""
        assert type_str == ""
        assert name_str == ""

    def test_orientation_only(self, parser):
        """Test label with only orientation marker."""
        label_text = "(h)"
        orientation, type_str, name_str = parser.detect_orientation_and_type(label_text)
        assert orientation == "h"
        assert type_str == ""
        assert name_str == ""

    def test_newlines_stripped_from_multiline_name(self, parser):
        """Test that newlines are converted to spaces in multi-line names."""
        parser.multi_line_dash = False
        label_text = "Castle View\nAnother Line (h) Copper"
        orientation, type_str, name_str = parser.detect_orientation_and_type(label_text)
        assert "\n" not in name_str
        assert orientation == "h"
        parser.multi_line_dash = False
