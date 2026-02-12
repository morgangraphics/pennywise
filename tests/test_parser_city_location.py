"""Tests for PennyParser class - city/location/neighborhood detection."""


class TestDetectCityLocationNeighborhood:
    """Test the detect_city_location_neighborhood method."""

    def test_two_lines_no_dash(self, parser):
        """Test two-line label without dash: City and Location."""
        label_text = "Anaheim\nDisneyland"
        city, location, neighborhood = parser.detect_city_location_neighborhood(label_text)
        assert city == "Anaheim"
        assert location == "Disneyland"
        assert neighborhood == ""

    def test_two_lines_with_dash(self, parser):
        """Test two-line label with dash: City and Neighborhood - Location."""
        label_text = "Anaheim\nDowntown Disney - World of Disney"
        city, location, neighborhood = parser.detect_city_location_neighborhood(label_text)
        assert city == "Anaheim"
        assert neighborhood == "Downtown Disney"
        # Without short_location flag, location includes full path
        assert "Downtown Disney" in location
        assert "World of Disney" in location

    def test_two_lines_with_dash_short_location(self, parser):
        """Test two-line label with dash and short_location flag."""
        parser.short_location = True
        label_text = "Anaheim\nDowntown Disney - World of Disney"
        city, location, neighborhood = parser.detect_city_location_neighborhood(label_text)
        assert city == "Anaheim"
        assert neighborhood == "Downtown Disney"
        assert location == "World of Disney"
        parser.short_location = False

    def test_three_lines_neighborhood_location(self, parser):
        """Test three-line label: City, Neighborhood, Location."""
        label_text = "San Francisco\nFisherman's Wharf\nMusée Mécanique Museum"
        city, location, neighborhood = parser.detect_city_location_neighborhood(label_text)
        assert city == "San Francisco"
        assert neighborhood == "Fisherman's Wharf"
        assert "Musée Mécanique Museum" in location

    def test_three_lines_with_dash_continuation(self, parser):
        """Test three-line label with dash in neighborhood line."""
        label_text = "San Francisco\nFisherman's Wharf - Pier 45\nMusée Mécanique Museum"
        city, location, neighborhood = parser.detect_city_location_neighborhood(label_text)
        assert city == "San Francisco"
        assert neighborhood == "Fisherman's Wharf"
        assert "Pier 45" in location
        assert "Musée Mécanique Museum" in location

    def test_multiline_with_continuation_words(self, parser):
        """Test multi-line location with continuation words (And, Of, &)."""
        label_text = "San Francisco\nDowntown\nStreet Name\nAnd Another Location"
        city, location, neighborhood = parser.detect_city_location_neighborhood(label_text)
        assert city == "San Francisco"
        assert neighborhood == "Downtown"
        # Continuation word should not add dash
        assert "And Another Location" in location

    def test_multiline_without_continuation_words(self, parser):
        """Test multi-line location without continuation words gets dash separator."""
        label_text = "San Francisco\nDowntown\nStreet Name\nAnother Location"
        city, location, neighborhood = parser.detect_city_location_neighborhood(label_text)
        assert city == "San Francisco"
        assert neighborhood == "Downtown"
        # Non-continuation word gets dash separator
        assert " - " in location

    def test_unicode_sanitization_in_labels(self, parser):
        """Test that unicode characters are sanitized."""
        label_text = 'San Francisco\nFisherman\'s Wharf\nMusée \u201cMécanique\u201d Museum'
        city, location, neighborhood = parser.detect_city_location_neighborhood(label_text)
        assert "Musée" in location
        assert '"' in location  # Smart quotes should be converted
        assert '\u201c' not in location

    def test_single_line_label(self, parser):
        """Test label with only one line (city)."""
        label_text = "Anaheim"
        city, location, neighborhood = parser.detect_city_location_neighborhood(label_text)
        assert city == "Anaheim"
        assert location == ""
        assert neighborhood == ""

    def test_empty_label(self, parser):
        """Test empty label text."""
        label_text = ""
        city, location, neighborhood = parser.detect_city_location_neighborhood(label_text)
        assert city == ""
        assert location == ""
        assert neighborhood == ""

    def test_location_overrides_neighborhood_on_short_location(self, parser):
        """Test that short_location flag uses only location part after dash."""
        parser.short_location = True
        label_text = "Anaheim\nDisneyland - Sleeping Beauty Castle"
        city, location, neighborhood = parser.detect_city_location_neighborhood(label_text)
        assert location == "Sleeping Beauty Castle"
        parser.short_location = False

    def test_en_dash_vs_hyphen(self, parser):
        """Test that both en-dash and hyphen are handled."""
        # Test with en-dash
        label_text_en = "Anaheim\nDowntown Disney – World of Disney"
        city1, loc1, neigh1 = parser.detect_city_location_neighborhood(label_text_en)

        # Test with hyphen
        label_text_hyphen = "Anaheim\nDowntown Disney - World of Disney"
        city2, loc2, neigh2 = parser.detect_city_location_neighborhood(label_text_hyphen)

        assert neigh1 == neigh2
        assert "Downtown Disney" in loc1
        assert "Downtown Disney" in loc2

    def test_whitespace_normalization(self, parser):
        """Test that leading/trailing whitespace is removed."""
        label_text = "  Anaheim  \n  Downtown Disney  \n  Location  "
        city, location, neighborhood = parser.detect_city_location_neighborhood(label_text)
        assert city == "Anaheim"
        assert neighborhood == "Downtown Disney"
        assert "Location" in location
        # Check no leading/trailing spaces
        assert not city.startswith(" ")
        assert not city.endswith(" ")
