import os
import sqlite3


class DatabaseValidationError(Exception):
    """Raised when SQLite database validation fails."""
    pass


def validate_sqlite_db(db_path: str) -> None:
    """
    Validates whether the given file is a usable SQLite database.
    Performs safety and integrity checks.

    Raises:
        DatabaseValidationError
    """

    # 1️⃣ Path exists and is a file
    if not os.path.exists(db_path):
        raise DatabaseValidationError(f"Database file not found: {db_path}")

    if not os.path.isfile(db_path):
        raise DatabaseValidationError("Provided path is not a file.")

    # 2️⃣ Extension check (soft validation)
    if not db_path.lower().endswith((".db", ".sqlite")):
        raise DatabaseValidationError(
            "Invalid file type. Expected a SQLite (.db or .sqlite) file."
        )

    try:
        # 3️⃣ Read-only connection (extra safety)
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()

        # 4️⃣ Integrity check
        result = cursor.execute("PRAGMA integrity_check;").fetchone()
        if not result or result[0].lower() != "ok":
            raise DatabaseValidationError("Database integrity check failed.")

        # 5️⃣ Check for user-defined tables (ignore sqlite_* tables)
        tables = cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name NOT LIKE 'sqlite_%';
        """).fetchall()

        if not tables:
            raise DatabaseValidationError("Database contains no user tables.")

    except sqlite3.Error as e:
        raise DatabaseValidationError(f"SQLite error: {e}")

    finally:
        try:
            conn.close()
        except Exception:
            pass
