"""
Migration: Add multi-dimensional bias score columns to bias_ratings table.

This migration adds 4 new columns to support multi-dimensional bias analysis:
- partisan_bias: Measures left/right political alignment
- affective_bias: Measures emotional language intensity
- framing_bias: Measures narrative framing and perspective
- sourcing_bias: Measures source diversity and viewpoint balance

All columns are nullable Float type to support gradual migration.
"""

import sqlite3


def run_migration(db_path: str = "veritas_news.db") -> bool:
    """
    Add 4 dimension columns to bias_ratings table.

    Args:
        db_path: Path to SQLite database file

    Returns:
        True if migration successful, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if migration already applied
        cursor.execute("PRAGMA table_info(bias_ratings)")
        columns = [row[1] for row in cursor.fetchall()]

        columns_to_add = [
            "partisan_bias",
            "affective_bias",
            "framing_bias",
            "sourcing_bias",
        ]

        for column in columns_to_add:
            if column not in columns:
                print(f"Adding column {column} to bias_ratings table")
                cursor.execute(
                    f"ALTER TABLE bias_ratings ADD COLUMN {column} REAL"
                )
            else:
                print(f"Column {column} already exists, skipping")

        conn.commit()
        conn.close()

        print("✓ Migration completed successfully")
        return True

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False


if __name__ == "__main__":
    # Run migration on default database
    run_migration()

