"""Tests for PennyParser class - city/location/neighborhood detection."""


class TestDetectCityLocationNeighborhood:
    """Test the detect_city_location_neighborhood method."""

    def test_two_lines_no_dash(self, parser):
        """Test two-line label without dash: City and Location."""
        label_text = "Anaheim\nDisneyland"
        city, location, neighborhood = parser.detect_city_location_neighborhood(
            label_text
        )
        assert city == "Anaheim"
        assert location == "Disneyland"
        assert neighborhood == ""

    def test_two_lines_with_dash(self, parser):
        """Test two-line label with dash: City and Location (no neighborhood)."""
        label_text = "Anaheim\nDowntown Disney - World of Disney"
        city, location, neighborhood = parser.detect_city_location_neighborhood(
            label_text
        )
        assert city == "Anaheim"
        # Two-line labels never populate neighborhood
        assert neighborhood == ""
        assert "Downtown Disney" in location
        assert "World of Disney" in location


    def test_three_lines_neighborhood_location(self, parser):
        """Test three-line label: City, Neighborhood, Location."""
        label_text = "San Francisco\nFisherman's Wharf\nMusée Mécanique Museum"
        city, location, neighborhood = parser.detect_city_location_neighborhood(
            label_text
        )
        assert city == "San Francisco"
        assert neighborhood == "Fisherman's Wharf"
        assert "Musée Mécanique Museum" in location

    def test_three_lines_with_dash_continuation(self, parser):
        """Test three-line label: line 2 with dash is kept as the full neighborhood."""
        label_text = (
            "San Francisco\nFisherman's Wharf - Pier 45\nMusée Mécanique Museum"
        )
        city, location, neighborhood = parser.detect_city_location_neighborhood(
            label_text
        )
        assert city == "San Francisco"
        # The entire line 2 becomes neighborhood (dash is not split here)
        assert neighborhood == "Fisherman's Wharf - Pier 45"
        assert "Musée Mécanique Museum" in location

    def test_multiline_with_continuation_words(self, parser):
        """Test multi-line label: lines 3+ are joined and first segment folds into neighborhood."""
        label_text = "San Francisco\nDowntown\nStreet Name\nAnd Another Location"
        city, location, neighborhood = parser.detect_city_location_neighborhood(
            label_text
        )
        assert city == "San Francisco"
        # Lines 3+ are joined with " - " then split; first part appended to neighborhood
        assert neighborhood == "Downtown - Street Name"
        assert "And Another Location" in location

    def test_multiline_without_continuation_words(self, parser):
        """Test multi-line label: first extra line folds into neighborhood, rest is location."""
        label_text = "San Francisco\nDowntown\nStreet Name\nAnother Location"
        city, location, neighborhood = parser.detect_city_location_neighborhood(
            label_text
        )
        assert city == "San Francisco"
        assert neighborhood == "Downtown - Street Name"
        assert location == "Another Location"

    def test_unicode_sanitization_in_labels(self, parser):
        """Test that unicode characters are sanitized."""
        label_text = (
            "San Francisco\nFisherman's Wharf\nMusée \u201cMécanique\u201d Museum"
        )
        city, location, neighborhood = parser.detect_city_location_neighborhood(
            label_text
        )
        assert "Musée" in location
        assert '"' in location  # Smart quotes should be converted
        assert "\u201c" not in location

    def test_single_line_label(self, parser):
        """Test label with only one line (city)."""
        label_text = "Anaheim"
        city, location, neighborhood = parser.detect_city_location_neighborhood(
            label_text
        )
        assert city == "Anaheim"
        assert location == ""
        assert neighborhood == ""

    def test_empty_label(self, parser):
        """Test empty label text."""
        label_text = ""
        city, location, neighborhood = parser.detect_city_location_neighborhood(
            label_text
        )
        assert city == ""
        assert location == ""
        assert neighborhood == ""


    def test_en_dash_vs_hyphen(self, parser):
        """Test that both en-dash and hyphen are handled."""
        # Test with en-dash
        label_text_en = "Anaheim\nDowntown Disney – World of Disney"
        city1, loc1, neigh1 = parser.detect_city_location_neighborhood(label_text_en)

        # Test with hyphen
        label_text_hyphen = "Anaheim\nDowntown Disney - World of Disney"
        city2, loc2, neigh2 = parser.detect_city_location_neighborhood(
            label_text_hyphen
        )

        assert neigh1 == neigh2
        assert "Downtown Disney" in loc1
        assert "Downtown Disney" in loc2

    def test_whitespace_normalization(self, parser):
        """Test that leading/trailing whitespace is removed."""
        label_text = "  Anaheim  \n  Downtown Disney  \n  Location  "
        city, location, neighborhood = parser.detect_city_location_neighborhood(
            label_text
        )
        assert city == "Anaheim"
        assert neighborhood == "Downtown Disney"
        assert "Location" in location
        # Check no leading/trailing spaces
        assert not city.startswith(" ")
        assert not city.endswith(" ")
