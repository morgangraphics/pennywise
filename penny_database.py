"""
penny_database.py

SQLite database handler for tracking pressed pennies and detecting new additions.
"""

import sqlite3
import hashlib
from datetime import datetime


class PennyDatabase:
    """SQLite database for storing and tracking pressed pennies."""

    def __init__(self, db_file: str = "pennies.db"):
        """
        Initialize the database connection and create tables if needed.

        Args:
            db_file (str): Path to SQLite database file.
        """
        self.db_file = db_file
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS pennies (
                id INTEGER PRIMARY KEY,
                state TEXT,
                city TEXT,
                neighborhood TEXT,
                location TEXT,
                name TEXT,
                orientation TEXT,
                type TEXT,
                year INTEGER,
                position INTEGER,
                hash TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_hash ON pennies(hash)")
        self.conn.commit()

    def _normalize_keys(self, penny_dict: dict) -> dict:
        """
        Normalize penny dict keys to lowercase for consistent access.

        Args:
            penny_dict (dict): Dictionary containing penny data.

        Returns:
            dict: Lowercased-key dictionary.
        """
        return {str(k).lower(): v for k, v in penny_dict.items()}

    def _hash_penny(self, penny_dict: dict) -> str:
        """
        Create a unique hash for a penny based on identifying fields.

        Args:
            penny_dict (dict): Dictionary containing penny data.

        Returns:
            str: SHA-256 hash of the penny's identifying characteristics.
        """
        normalized = self._normalize_keys(penny_dict)
        key = f"{normalized.get('state', '')}|{normalized.get('city', '')}|{normalized.get('location', '')}|{normalized.get('name', '')}|{normalized.get('orientation', '')}"
        return hashlib.sha256(key.encode()).hexdigest()

    def penny_exists(self, penny_dict: dict) -> bool:
        """
        Check if a penny already exists in the database.

        Args:
            penny_dict (dict): Dictionary containing penny data.

        Returns:
            bool: True if penny exists, False otherwise.
        """
        hash_val = self._hash_penny(penny_dict)
        cursor = self.conn.execute("SELECT id FROM pennies WHERE hash = ?", (hash_val,))
        return cursor.fetchone() is not None

    def add_penny(self, penny_dict: dict) -> bool:
        """
        Add a penny to the database if it doesn't already exist.

        Args:
            penny_dict (dict): Dictionary containing penny data with keys:
                state, city, neighborhood, location, name, orientation, type, year, position

        Returns:
            bool: True if penny was added, False if it already existed.
        """
        normalized = self._normalize_keys(penny_dict)
        hash_val = self._hash_penny(normalized)
        try:
            self.conn.execute(
                """
                INSERT INTO pennies 
                (state, city, neighborhood, location, name, orientation, type, year, position, hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    normalized.get("state", ""),
                    normalized.get("city", ""),
                    normalized.get("neighborhood", ""),
                    normalized.get("location", ""),
                    normalized.get("name", ""),
                    normalized.get("orientation", ""),
                    normalized.get("type", ""),
                    normalized.get("year", ""),
                    normalized.get("position", ""),
                    hash_val,
                ),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Penny already exists
            return False

    def get_penny_count(self) -> int:
        """
        Get total number of unique pennies in database.

        Returns:
            int: Number of pennies in database.
        """
        cursor = self.conn.execute("SELECT COUNT(*) FROM pennies")
        return cursor.fetchone()[0]

    def get_pennies_by_state(self, state: str) -> list:
        """
        Get all pennies for a specific state.

        Args:
            state (str): State name.

        Returns:
            list: List of penny records.
        """
        cursor = self.conn.execute(
            "SELECT * FROM pennies WHERE state = ? ORDER BY year, city", (state,)
        )
        return cursor.fetchall()

    def get_pennies_by_year(self, year: int) -> list:
        """
        Get all pennies added in a specific year.

        Args:
            year (int): Year to filter by.

        Returns:
            list: List of penny records.
        """
        cursor = self.conn.execute(
            "SELECT * FROM pennies WHERE year = ? ORDER BY state, city", (year,)
        )
        return cursor.fetchall()

    def get_new_pennies_since(self, since_datetime: datetime) -> list:
        """
        Get all pennies added since a specific datetime.

        Args:
            since_datetime (datetime): Datetime to filter from.

        Returns:
            list: List of newly added penny records.
        """
        cursor = self.conn.execute(
            "SELECT * FROM pennies WHERE created_at > ? ORDER BY created_at DESC",
            (since_datetime.isoformat(),),
        )
        return cursor.fetchall()

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
