#!/usr/bin/env python3
"""
penny_parser.py

CLI tool for parsing specially formatted Word (.docx) documents containing
vertical-stacked label tables into normalized CSV files.

Usage:
    python penny_parser.py --input il.docx --output il.csv
"""

import csv
import argparse
import mimetypes
import re
import logging
import sys
import io
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from penny_database import PennyDatabase


class PennyParser:
    """Parser for pressed-penny DOCX documents."""

    # Separator dash pattern (avoid splitting in-word like "two-way" or "Buc-ees")
    dash_regex = r"(?<!\w)[-–—](?!\w)"

    def __init__(self, log_file: str = "penny_parser.log", db_file: str = "pennies.db"):
        """
        Initialize the parser with logging configuration.

        Args:
            log_file (str): Path to the log file.
            db_file (str): Path to SQLite database file.
        """
        self.log_file = log_file
        self.logger = self.setup_logging(log_file, with_console=True)
        self.labels_logger = self.setup_logging(
            "labels.log", logger_name=f"{__name__}.labels", with_console=False
        )
        self.write_mode = "w"
        self.new_only = False
        self.multi_line_dash = False
        self.db = PennyDatabase(db_file)
        self.continuation_words = (
            "And",
            "and",
            "&",
            "Of",
            "of",
        )  # Words/symbols that indicate continuation without separator
        self.state_map = {
            "al": "Alabama",
            "ak": "Alaska",
            "az": "Arizona",
            "ar": "Arkansas",
            "ca": "California",
            "co": "Colorado",
            "ct": "Connecticut",
            "de": "Delaware",
            "dc": "District of Columbia",
            "fl": "Florida",
            "ga": "Georgia",
            "hi": "Hawaii",
            "id": "Idaho",
            "il": "Illinois",
            "in": "Indiana",
            "ia": "Iowa",
            "ks": "Kansas",
            "ky": "Kentucky",
            "la": "Louisiana",
            "me": "Maine",
            "md": "Maryland",
            "ma": "Massachusetts",
            "mi": "Michigan",
            "mn": "Minnesota",
            "ms": "Mississippi",
            "mo": "Missouri",
            "mt": "Montana",
            "ne": "Nebraska",
            "nv": "Nevada",
            "nh": "New Hampshire",
            "nj": "New Jersey",
            "nm": "New Mexico",
            "ny": "New York",
            "nc": "North Carolina",
            "nd": "North Dakota",
            "oh": "Ohio",
            "ok": "Oklahoma",
            "or": "Oregon",
            "pa": "Pennsylvania",
            "ri": "Rhode Island",
            "sc": "South Carolina",
            "sd": "South Dakota",
            "tn": "Tennessee",
            "tx": "Texas",
            "ut": "Utah",
            "vt": "Vermont",
            "va": "Virginia",
            "wa": "Washington",
            "wv": "West Virginia",
            "wi": "Wisconsin",
            "wy": "Wyoming",
            # Add territories here if desired
        }

    def setup_logging(
        self, log_file: str, logger_name: str = None, with_console: bool = True
    ):
        """
        Configure logging to output to file and optionally console.

        Args:
            log_file (str): Path to the log file.
            logger_name (str): Name for the logger. Defaults to __name__.
            with_console (bool): Whether to include console output. Defaults to True.
        """
        logger = logging.getLogger(logger_name or __name__)
        logger.setLevel(logging.DEBUG)

        # Close and remove existing handlers to prevent resource leaks
        for handler in logger.handlers[:]:
            handler.flush()
            # Only close handlers that manage their own streams (e.g., FileHandler)
            # FileHandler and its subclasses (RotatingFileHandler, etc.) are safely closed
            # Don't close StreamHandlers that may wrap sys.stdout/stderr
            if isinstance(handler, logging.FileHandler):
                handler.close()
            logger.removeHandler(handler)

        # Console handler - INFO and above (if enabled)
        if with_console:
            # Use sys.stderr directly to avoid closing the underlying buffer
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter("%(levelname)s: %(message)s")
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)

        # File handler - DEBUG and above (more verbose)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Prevent propagation to parent logger if this is a child logger
        if logger_name and logger_name != __name__:
            logger.propagate = False

        return logger

    def parse_state_from_filename(self, filename: str) -> str:
        """
        Extract state name from filename using state_map as source of truth.
        
        Handles various filename formats:
        - ca.docx, ca-new.docx, ca_backup.docx → California
        - massachusetts.docx, massachusetts-old.docx → Massachusetts
        - new.york.docx, new-york.docx → New York

        Args:
            filename (str): The DOCX filename.

        Returns:
            str: Full state name, e.g., 'Colorado'.
        """
        stem = Path(filename).stem.lower()
        # Normalize: replace separators with spaces to get clean tokens
        normalized_stem = stem.replace('-', ' ').replace('_', ' ').replace('.', ' ')
        tokens = normalized_stem.split()

        # First, check if any state abbreviation (key) appears as a full token
        # Sort by length descending to prioritize longer abbreviations
        sorted_abbrevs = sorted(self.state_map.items(), key=lambda x: len(x[0]), reverse=True)
        for abbrev, state_name in sorted_abbrevs:
            abbrev_lower = abbrev.lower()
            # Match abbreviation as a complete token (e.g., "dc" in "washington dc")
            if any(token == abbrev_lower for token in tokens):
                return state_name
            # Also support filenames that start with the abbreviation followed by a separator
            if stem == abbrev_lower or stem.startswith(abbrev_lower + '-') or stem.startswith(abbrev_lower + '_') or stem.startswith(abbrev_lower + '.'):
                return state_name

        # Second, check if any full state name (value) appears as token(s)
        # Sort by length descending to match longer names first (e.g., "new york" before "ne")
        sorted_states = sorted(self.state_map.items(), key=lambda x: len(x[1]), reverse=True)
        for abbrev, state_name in sorted_states:
            state_lower = state_name.lower()
            state_tokens = state_lower.split()
            # Try to match the state name as a contiguous sequence of tokens
            if len(state_tokens) == 1:
                if any(token == state_lower for token in tokens):
                    return state_name
            else:
                n = len(state_tokens)
                for i in range(len(tokens) - n + 1):
                    if tokens[i:i + n] == state_tokens:
                        return state_name
            # Fallback: match "newyork" style filenames with no separators
            if state_lower.replace(' ', '') in stem:
                return state_name
        # Fallback: capitalize the stem
        return stem.capitalize()

    def split_and_strip(self, text: str, delimiter: str = None) -> list:
        """
        Split text on a delimiter and strip whitespace from each resulting part.

        Args:
            text (str): The text to split.
            delimiter (str): Regex pattern to split on. Defaults to self.dash_regex.

        Returns:
            list: List of stripped text parts.
        """
        if delimiter is None:
            delimiter = self.dash_regex
        return [part.strip() for part in re.split(delimiter, text)]

    def cell_is_retired(self, cell) -> bool:
        """
        Determine whether a DOCX table cell is 'retired' by checking whether the
        shading fill color is pink/rose.

        Args:
            cell (docx.table._Cell): A DOCX table cell.

        Returns:
            bool: True if the cell background corresponds to a retired label.
        """
        tcPr = cell._tc.get_or_add_tcPr()
        shd = tcPr.find(qn("w:shd"))
        if shd is not None:
            fill = shd.get(qn("w:fill"))
            if fill:
                fill = fill.lower()
                # Colors typically used in the documents for retired pennies
                # return fill in ("ffcccc", "ffc0cb", "f4cccc", "e6b8af")
                return fill in ("f2dbdb")
        return False

    def is_table_of_contents(self, block) -> bool:
        """
        Determine if a block is part of a table of contents.

        Checks for paragraph style names containing 'TOC' (case-insensitive).
        Actual Heading paragraphs use "Heading" styles, not "TOC" styles.

        Args:
            block: A paragraph or table object.

        Returns:
            bool: True if the block is part of TOC.
        """
        if (
            hasattr(block, "style")
            and block.style
            and "toc" in block.style.name.lower()
        ):
            return True

        return False

    def build_h2_h3_map(self, document) -> dict:
        """
        Build a map of H2 headings and whether they have H3s below them.

        This allows us to determine if an H2 is just a neighborhood (has H3s below)
        or both neighborhood AND location (no H3s below).

        Args:
            document: A python-docx Document object.

        Returns:
            dict: Mapping of H2 text -> bool (True if H2 has H3s below it)
        """
        h2_h3_map = {}
        current_h2 = None

        for para in document.paragraphs:
            if not hasattr(para, "style") or not para.style:
                continue

            style_name = para.style.name.lower()
            text = para.text.strip()

            if not text:
                continue

            if "heading 2" in style_name:
                current_h2 = text
                if current_h2 not in h2_h3_map:
                    h2_h3_map[current_h2] = False
            elif "heading 3" in style_name and current_h2:
                h2_h3_map[current_h2] = True

        return h2_h3_map

    def sanitize_for_csv(self, text: str) -> str:
        """
        Replace problematic unicode characters with ASCII equivalents for safe CSV output.

        Args:
            text (str): The text to sanitize.

        Returns:
            str: Sanitized text safe for CSV.
        """
        # Common unicode replacements
        replacements = {
            "\u2013": "-",  # en dash (U+2013)
            "\u2014": "-",  # em dash (U+2014)
            "\u2019": "'",  # right single quotation mark / apostrophe (U+2019)
            "\u2018": "'",  # left single quotation mark (U+2018)
            "\u201c": '"',  # left double quotation mark (U+201C)
            "\u201d": '"',  # right double quotation mark (U+201D)
            "\u02bc": "'",  # modifier letter apostrophe (U+02BC)
            "\u00b4": "'",  # acute accent (U+00B4)
            "\u201b": "'",  # reversed comma quotation mark (U+201B)
            "\u2032": "'",  # prime symbol (U+2032)
            "\u2026": "...",  # ellipsis (U+2026)
            "\u00ae": "(R)",  # registered trademark (U+00AE)
            "\u2122": "(TM)",  # trademark (U+2122)
            "\u00a9": "(C)",  # copyright (U+00A9)
            "\u00b0": "deg",  # degree symbol (U+00B0)
            "&": "&",  # ampersand (already safe, but explicit)
        }

        result = text
        for unicode_char, ascii_char in replacements.items():
            result = result.replace(unicode_char, ascii_char)

        return result

    def normalize_cell_text(self, cell) -> str:
        """
        Extract text from a DOCX table cell and strip whitespace.

        Args:
            cell (docx.table._Cell): Table cell.

        Returns:
            str: Cleaned text string.
        """
        return cell.text.strip()

    def strip_newlines_and_returns(self, text: str) -> str:
        """
        Remove newline and carriage return characters from text.

        Args:
            text (str): The text to clean.

        Returns:
            str: Text with \\n and \\r characters removed.
        """
        return text.replace("\n", " ").replace("\r", " ")

    def detect_city_location_neighborhood(self, label_text: str):
        """
        Parse a top label cell text into (city, location, neighborhood).

        Rules:
          Line 1: City
          If exactly 2 lines:
            Line 2 = Location (neighborhood stays empty)
          If more than 2 lines:
            Line 2 = Neighborhood
            Lines 3+ joined with " - " = combined location string
            Split combined on dash separators between word boundaries (commas are ignored):
              first part  -> appended to Neighborhood: "Neighborhood - first_part"
              remaining   -> Location

        EXAMPLE:
            Bay Lake
            Disney's Hollywood Studios
            Echo Lake
            Frozen Fractal Gifts
            =>
            ('Bay Lake', 'Frozen Fractal Gifts', "Disney's Hollywood Studios - Echo Lake")

        Args:
            label_text (str): The raw label text from table cell.

        Returns:
            tuple: (city, location, neighborhood)
        """
        # Separator: word-boundary dashes only (excludes hyphenated words like Buc-ees)
        # Commas are intentionally excluded — business names like "Inc." or "Pub & Inn"
        # contain commas that must not be treated as location separators.
        sep_regex = r"(?<![\w])[-\u2013\u2014](?![\w])"

        city = ""
        location = ""
        neighborhood = ""

        lines = [ln.strip() for ln in label_text.splitlines() if ln.strip()]

        if not lines:
            return city, location, neighborhood

        # Line 1 is always the city
        city = self.sanitize_for_csv(lines[0])

        if len(lines) == 2:
            # Exactly two lines: Line 2 is the Location (no neighborhood)
            location = self.sanitize_for_csv(lines[1])

        elif len(lines) > 2:
            # Line 2 is the Neighborhood
            neighborhood = self.sanitize_for_csv(lines[1])

            # Lines 3+ combined with " - "
            combined = " - ".join(lines[2:])

            # Split combined location on separators
            parts = self.split_and_strip(combined, sep_regex)
            parts = [p for p in parts if p]  # remove empty strings

            if len(parts) > 1:
                # First part appended to neighborhood
                neighborhood = neighborhood + " - " + self.sanitize_for_csv(parts[0])
                location = self.sanitize_for_csv(" - ".join(parts[1:]))
            else:
                location = self.sanitize_for_csv(combined)

        return city, location, neighborhood

    def detect_orientation_and_type(self, label_text: str):
        """
        Parse a label string into (orientation, type, name).

        EXAMPLE:
            'Denver Colorado - Mile High City (h) Copper Penny'
            =>
            ('h', 'Copper Penny', 'Denver Colorado - Mile High City')

        Args:
            label_text (str): The raw label text.

        Returns:
            tuple: (orientation, type_str, name_str)
        """
        orient_match = re.search(r"\((h|v)\)", label_text, re.IGNORECASE)
        if not orient_match:
            return "", "", label_text

        orientation = orient_match.group(1).lower()
        lines = label_text.splitlines()

        if len(lines) == 1:
            name_str = label_text[: orient_match.start()].strip()

        # Handles mutli-line names
        if len(lines) > 1:
            if self.multi_line_dash:
                # Allow dash in multi-line names
                name_str = (
                    self.strip_newlines_and_returns(
                        lines[0] + " - " + " ".join(lines[1 : len(lines) - 1])
                    )
                    if len(lines) > 1
                    else ""
                )
            else:
                name_str = (
                    self.strip_newlines_and_returns(" ".join(lines[0 : len(lines) - 1]))
                    if len(lines) > 1
                    else ""
                )

        type_str = label_text[orient_match.end() :].strip()

        return orientation, type_str, name_str

    def rows_from_vertical_pairs(self, table):
        """
        Yield logical rows from a DOCX table by grouping vertically stacked cells.

        Each column in the table contains vertically paired entries:
        (row0,row1), (row2,row3), etc.

        Skips odd-indexed columns (1, 3, 5) which are spacer columns in the 7-column format.
        Only processes even-indexed columns (0, 2, 4, 6) which contain actual label data.

        Position index resets for each pair of rows:
        - Rows 0-1: positions 1-4
        - Rows 2-3: positions 5-8
        - Rows 4-5: positions 9-12, etc.

        Args:
            table (docx.table.Table): The DOCX table.

        Yields:
            tuple: (cell1, cell2, position_index)
        """
        num_rows = len(table.rows)
        num_cols = len(table.columns)
        # Count only data columns at even indices (col_index 0, 2, 4, 6, etc.)
        num_data_cols = (num_cols + 1) // 2  # For 7 columns: 4 data columns

        def safe_cell(row_idx: int, col_idx: int):
            try:
                return table.cell(row_idx, col_idx)
            except IndexError:
                return None

        data_col_num = 0  # Track which data column we're on (0, 1, 2, 3...)
        for col_index in range(num_cols):
            # Process only even-indexed columns (0, 2, 4, 6, etc.) which contain data
            if col_index % 2 == 0:  # Skip odd indices (1, 3, 5, etc.) which are spacers
                for r in range(0, num_rows, 2):
                    cell1 = safe_cell(r, col_index)
                    cell2 = safe_cell(r + 1, col_index) if r + 1 < num_rows else None
                    if cell1 is None:
                        continue
                    # Position calculation: data_col_num + 1 + (row_pair_index * num_data_cols)
                    row_pair_index = r // 2
                    position = data_col_num + 1 + (row_pair_index * num_data_cols)
                    yield (cell1, cell2, position)
                data_col_num += 1

    def parse_docx_to_rows(self, filename: str) -> list:
        """
        Parse a DOCX file of pressed-penny label tables into CSV row dictionaries.

        This function implements all custom rules:
          - State is derived from filename
          - City from paragraph headers
          - Neighborhood left empty by default
          - Location from table header
          - Position determined by *column index* counting empty columns
          - Retired detected by pink/rose cell shading
          - Orientation & Type parsed from label
          - Quantity defaults to 1

        Args:
            filename (str): The .docx input file.

        Returns:
            list of dict: Parsed CSV rows.
        """
        document = Document(filename)
        state = self.parse_state_from_filename(filename)

        # Build map of H2s and whether they have H3s below them
        h2_has_h3_map = self.build_h2_h3_map(document)

        csv_rows = []
        new_pennies = []  # Collect new pennies for batch insert at the end
        row_dict = {
            "State": "",
            "City": "",
            "Neighborhood": "",
            "Location": "",
            "Orientation": "",
            "Name": "",
            "Type": "",
            "Year": "",
            "Position": "",
            "Retired": "",
            "Set #": "",
            "Quantity": 1,
            "Need": "",
        }

        current_set = 0  # Counter for sets within a year
        last_year = None  # Track the last year to detect when it changes
        current_h2_neighborhood = ""  # Track original H2 neighborhood for H3s to reference

        # Initialize row_data so tables before any Heading 1 don't crash
        row_data = row_dict.copy()

        # Iterate through document body elements in order (maintains document flow)
        for element in document.element.body:
            # Check if it's a paragraph
            if element.tag.endswith("p"):
                # Get the paragraph object
                para = None
                for p in document.paragraphs:
                    if p._element == element:
                        para = p
                        break

                if para is None:
                    continue

                # Skip TOC blocks
                if self.is_table_of_contents(para):
                    continue

                text = para.text.strip()
                if not text:
                    continue

                # Determine heading level and update appropriate variable from Document Map Headings
                if hasattr(para, "style") and para.style:
                    style_name = para.style.name.lower()

                    if "heading 1" in style_name:
                        # City
                        row_data = row_dict.copy()
                        row_data.update(
                            {
                                "State": self.sanitize_for_csv(state),
                                "City": self.sanitize_for_csv(text),
                            }
                        )
                        current_set = 0  # Reset set counter for new city
                        last_year = None  # reset year
                        current_h2_neighborhood = ""  # reset H2 neighborhood for new city

                    elif "heading 2" in style_name:
                        # H2 can be a neighborhood OR a neighborhood+location

                        self.logger.info(f"LEVEL 2 Heading detected: {text}")

                        # Check if this H2 has H3s below it
                        h2_has_h3 = h2_has_h3_map.get(text, False)

                        if h2_has_h3:
                            # H2 is the neighborhood; H3s will supply the location
                            current_h2_neighborhood = self.sanitize_for_csv(text)
                            row_data.update(
                                {
                                    "Neighborhood": current_h2_neighborhood,
                                    "Location": "",
                                }
                            )
                        else:
                            # H2 is a standalone location; neighborhood stays empty
                            current_h2_neighborhood = ""
                            row_data.update(
                                {
                                    "Neighborhood": "",
                                    "Location": self.sanitize_for_csv(text),
                                }
                            )

                    elif "heading 3" in style_name:
                        """
                        H3 = Location.

                        If H3 contains a dash separator between word boundaries:
                          - Split on the dash separator
                          - first_part appended to H2 Neighborhood:
                              "H2-Neighborhood - first_part"
                          - remaining parts -> Location
                        If H3 has no such separator:
                          - Location = H3 text
                          - Neighborhood unchanged (what H2 set)

                        Note: Commas are not treated as separators; they may appear in names
                        (e.g., "Something, Inc.") without triggering a split.
                        """
                        self.logger.info(f"LEVEL 3 Heading detected: {text}")

                        # Separator: word-boundary dashes only (excludes hyphenated words like Buc-ees)
                        # Commas are intentionally excluded — business names like "Inc." or "Pub & Inn"
                        # contain commas that must not be treated as location separators.
                        sep_regex = r"(?<![\w])[-\u2013\u2014](?![\w])"

                        # Use the original H2 neighborhood (not what a previous H3 wrote)
                        h2_neighborhood = current_h2_neighborhood

                        if re.search(sep_regex, text):
                            # Split H3 on separator
                            parts = self.split_and_strip(text, sep_regex)
                            parts = [p for p in parts if p]
                            first_part = parts[0]
                            remaining = " - ".join(parts[1:]) if len(parts) > 1 else ""

                            # Append first_part to H2 neighborhood
                            if h2_neighborhood:
                                neighborhood = h2_neighborhood + " - " + self.sanitize_for_csv(first_part)
                            else:
                                neighborhood = self.sanitize_for_csv(first_part)

                            location = self.sanitize_for_csv(remaining)
                        else:
                            # No separator: H3 is purely the location
                            neighborhood = h2_neighborhood
                            location = self.sanitize_for_csv(text)

                        row_data.update(
                            {
                                "Neighborhood": neighborhood,
                                "Location": location,
                            }
                        )

                        # Reset year after reaching a new level 3 heading
                        last_year = None

                        self.logger.debug(f"Level 3: {row_data.copy()}")

                    elif "heading 4" in style_name:

                        self.logger.info(f"LEVEL 4: Heading detected: {text}")

                        # Year heading - check if it's a new year to reset set counter
                        if text != last_year:
                            current_set = 0
                            last_year = text
                        row_data.update({"Year": text})

                        self.logger.debug(f"Level 4: {row_data.copy()}")

            # Check if it's a table
            elif element.tag.endswith("tbl"):
                # Get the table object
                table = None

                # copy of row_data to avoid mutation issues
                cell_data = row_data.copy()

                # tmp storage to look for multiple instances with different types
                position_stor = {}

                for t in document.tables:
                    if t._element == element:
                        table = t
                        break

                if table is None:
                    continue

                # Increment set counter for each table under a year
                if cell_data.get("Year"):
                    current_set += 1

                # Process all vertically paired rows
                for cell1, cell2, position in self.rows_from_vertical_pairs(table):

                    txt1 = self.normalize_cell_text(cell1)
                    txt2 = self.normalize_cell_text(cell2) if cell2 else ""

                    # skip if both cells are empty
                    if not txt1 and not txt2:
                        continue

                    # if penny is marked as retired
                    retired = self.cell_is_retired(cell1) and (
                        cell2 and self.cell_is_retired(cell2)
                    )

                    # Top Labels - Parse and validate against Document Map
                    if txt1:
                        city, location, neighborhood = (
                            self.detect_city_location_neighborhood(txt1)
                        )

                        # Human-readable logging of parsed vs document map
                        # self.labels_logger.info(f"TOP LABEL     : city='{city}' | location='{location}' | neighborhood='{neighborhood}'")
                        # self.labels_logger.info(f"DOCUMENT MAP  : city='{cell_data.get('City')}' | location='{cell_data.get('Location')}' | neighborhood='{cell_data.get('Neighborhood')}'")
                        # self.labels_logger.info(f"{'='*80}\n")

                        # Check for mismatches between parsed label and document map
                        mismatch_msg = ""

                        if (
                            city
                            and city != cell_data.get("City")
                            or location
                            and location != cell_data.get("Location")
                            or neighborhood
                            and neighborhood != cell_data.get("Neighborhood")
                        ):
                            mismatch_msg += f"\n{'='*60}\n"
                            mismatch_msg += f"Mismatch for {self.sanitize_for_csv(self.strip_newlines_and_returns(txt1))}"

                        if city and city != cell_data.get("City"):
                            mismatch_msg += f"\n  City Mismatch:\n    Document Map City: '{cell_data.get('City')}'\n    Parsed Label City: '{city}'"
                        if location and location != cell_data.get("Location"):
                            mismatch_msg += f"\n  Location Mismatch:\n    Document Map Location: '{cell_data.get('Location')}'\n    Parsed Label Location: '{location}'"
                        if neighborhood and neighborhood != cell_data.get(
                            "Neighborhood"
                        ):
                            mismatch_msg += f"\n  Neighborhood Mismatch:\n    Document Map Neighborhood: '{cell_data.get('Neighborhood')}'\n    Parsed Label Neighborhood: '{neighborhood}'"

                        if mismatch_msg:
                            self.labels_logger.warning(mismatch_msg)

                    # Bottom Labels - Parse penny details
                    if txt2:
                        orientation, type_str, name_str = (
                            self.detect_orientation_and_type(txt2)
                        )

                        # Position is now correctly calculated in rows_from_vertical_pairs
                        # No need to adjust it here

                        # Create hash to detect duplicates (same location/name/orientation but different type)
                        stor_hash = f"{cell_data.get('Location')}|{self.sanitize_for_csv(self.strip_newlines_and_returns(name_str))}|{orientation}"

                        if stor_hash in position_stor:
                            self.logger.debug(
                                "Duplicate detected: Same Location/Name/Orientation with different Type (likely Copper vs Zinc Penny)"
                            )
                            position = position_stor.get(stor_hash)

                        row_to_append = cell_data.copy()
                        row_to_append.update({"Retired": "Yes" if retired else ""})
                        row_to_append.update(
                            {"Set #": current_set if current_set > 1 else ""}
                        )
                        row_to_append.update({"Orientation": orientation})
                        row_to_append.update({"Type": type_str})
                        row_to_append.update({"Position": position})
                        row_to_append.update(
                            {
                                "Name": self.sanitize_for_csv(
                                    self.strip_newlines_and_returns(name_str)
                                )
                            }
                        )

                        # Check if penny exists in database
                        is_new = not self.db.penny_exists(row_to_append)

                        # If penny is new, add to batch for later insertion
                        if is_new:
                            new_pennies.append(row_to_append)
                            self.logger.debug(
                                f"New penny found: {row_to_append['Name']} at {row_to_append['Location']}"
                            )
                        else:
                            self.logger.debug(
                                f"Existing penny: {row_to_append['Name']} at {row_to_append['Location']}"
                            )

                        # Add to output based on --new-only flag
                        if self.new_only:
                            # Only output new pennies
                            if is_new:
                                csv_rows.append(row_to_append)
                        else:
                            # Output all pennies
                            csv_rows.append(row_to_append)

                        position_stor.update({stor_hash: position})

        # Batch insert all new pennies at the end
        if new_pennies:
            added_count = self.db.add_pennies_batch(new_pennies)
            self.logger.info(f"Added {added_count} new pennies to database")

        return csv_rows

    def write_csv(self, rows, out_path: str):
        """
        Write parsed rows into a CSV file.

        Args:
            rows (list of dict): Parsed data rows.
            out_path (str): Path for output CSV file.
        """
        header = [
            "State",
            "City",
            "Neighborhood",
            "Location",
            "Name",
            "Orientation",
            "Type",
            "Year",
            "Position",
            "Retired",
            "Set #",
            "Quantity",
            "Need",
        ]

        with open(out_path, self.write_mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=header, quoting=csv.QUOTE_ALL)
            # Only write header if creating new file
            if self.write_mode == "w":
                writer.writeheader()
            writer.writerows(rows)

    def run(
        self,
        input_file: str,
        output_file: str,
        new_only: bool = False,
        multi_line_dash: bool = False,
        write_mode_override: str = None,
    ):
        """
        Run the parser with input and output files.

        Args:
            input_file (str): Path to input DOCX file.
            output_file (str): Path to output CSV file.
            new_only (bool): Only extract pennies not in database.
            multi_line_dash (bool): Allow dash separator in multi-line descriptions.
            write_mode_override (str): Override write mode ('w' or 'a'). If None, prompt user.
        """
        input_path = Path(input_file)
        if not input_path.exists():
            self.logger.error(f"Input file does not exist: {input_file}")
            return

        # Validate MIME type for Microsoft Word .docx format
        mime_type, _ = mimetypes.guess_type(input_file)
        if (
            mime_type
            != "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            # self.logger.error(f"Input file is not a valid Microsoft Word (.docx) file. Got MIME type: {mime_type}")
            print(
                f"ERROR: Input file is not a valid Microsoft Word (.docx) file. Got MIME type: {mime_type}"
            )
            return

        # Configure labels logger per input state/file (e.g., labels_dc.log)
        input_stem = Path(input_file).stem.lower()
        labels_log_file = f"labels_{input_stem}.log"
        self.labels_logger = self.setup_logging(
            labels_log_file, logger_name=f"{__name__}.labels", with_console=False
        )

        # Check if output file exists and get user preference before processing
        output_path = Path(output_file)
        write_mode = (
            write_mode_override or "w"
        )  # Default to write (overwrite) unless overridden

        if output_path.exists() and not write_mode_override:
            print(f"\nFile '{output_file}' already exists.")
            while True:
                choice = input(
                    "Choose an action:\n  1) Overwrite\n  2) Append\n  3) Backup and create new\n  4) Cancel\nEnter choice (1/2/3/4): "
                ).strip()

                if choice == "1":
                    if new_only:
                        print(
                            "\n⚠️  WARNING: Using 'Overwrite' with '--new-only' flag will DELETE all existing data!"
                        )
                        confirm = (
                            input("Are you sure you want to proceed? (yes/no): ")
                            .lower()
                            .strip()
                        )
                        if confirm == "no" or confirm == "n":
                            print("Operation cancelled.")
                            return
                    print("Overwriting existing file...")
                    write_mode = "w"
                    break
                elif choice == "2":
                    print("Appending to existing file...")
                    write_mode = "a"
                    break
                elif choice == "3":
                    # Create backup with timestamp
                    from datetime import datetime

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_path = (
                        output_path.parent
                        / f"{output_path.stem}_backup_{timestamp}{output_path.suffix}"
                    )
                    output_path.rename(backup_path)
                    print(f"Original file backed up to: {backup_path}")
                    write_mode = "w"
                    break
                elif choice == "4":
                    print("Operation cancelled.")
                    return
                else:
                    print("Invalid choice. Please enter 1, 2, 3, or 4.")

        self.write_mode = write_mode
        self.new_only = new_only
        self.multi_line_dash = multi_line_dash

        rows = self.parse_docx_to_rows(input_file)
        self.write_csv(rows, output_file)

        self.logger.info(f"Successfully parsed {len(rows)} rows.")
        self.logger.info(f"Output written to {output_file}")

    def run_file(
        self,
        input_file: str,
        output_file: str,
        multi_line_dash: bool,
        new_only: bool = False,
        write_mode_override: str = None,
    ):
        """Alias for run() method to match directory processing call signature."""
        return self.run(
            input_file,
            output_file,
            new_only,
            multi_line_dash,
            write_mode_override,
        )


def parse_arguments(args=None):
    """
    Parse command-line arguments.

    Args:
        args: List of argument strings to parse. If None, uses sys.argv.

    Returns:
        Namespace object containing parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Parse a pressed-penny DOCX file into a normalized CSV."
    )

    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to input .docx file or directory containing .docx files",
    )

    parser.add_argument(
        "--output", "-o", required=True, help="Path to output .csv file"
    )

    parser.add_argument(
        "--multi-line-dash",
        "-mld",
        dest="multi_line_dash",
        action="store_true",
        help="Will allow for dash separator in multi-line descriptions e.g. The Aristocats\n Something becomes The Aristocats - Something",
    )

    parser.add_argument(
        "--new-only",
        "-n",
        dest="new_only",
        action="store_true",
        help="Only extract pennies not already in the database",
    )

    return parser.parse_args(args)


def main():
    """
    Main entry point for the CLI.
    Uses argparse to collect command line arguments and perform parsing.
    """
    args = parse_arguments()

    penny_parser = PennyParser()

    # Handle directory or file input
    input_path = Path(args.input)

    if input_path.is_dir():
        # Process all .docx files in directory
        docx_files = sorted(input_path.glob("*.docx"))
        if not docx_files:
            print(f"No .docx files found in {args.input}")
            return

        for i, docx_file in enumerate(docx_files):
            print(f"\nProcessing {i+1}/{len(docx_files)}: {docx_file.name}")
            # For directory processing, always append (except first file)
            output_mode = "w" if i == 0 else "a"
            penny_parser.run_file(
                str(docx_file),
                args.output,
                args.multi_line_dash,
                args.new_only,
                write_mode_override=output_mode,
            )
    else:
        # Process single file
        penny_parser.run(
            args.input,
            args.output,
            new_only=args.new_only,
            multi_line_dash=args.multi_line_dash,
        )


if __name__ == "__main__":
    main()
