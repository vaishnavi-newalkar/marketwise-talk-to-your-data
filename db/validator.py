"""
Database Validator

Validates SQLite database files for:
- File integrity
- Database structure
- Security concerns
"""

import os
import sqlite3
from typing import List, Tuple


class DatabaseValidationError(Exception):
    """Raised when database validation fails."""
    pass


# Maximum file size (100 MB)
MAX_DB_SIZE = 100 * 1024 * 1024

# Minimum file size (SQLite header is 100 bytes)
MIN_DB_SIZE = 100

# SQLite magic bytes
SQLITE_MAGIC = b"SQLite format 3\x00"


def validate_sqlite_db(db_path: str) -> bool:
    """
    Validates a SQLite database file.
    
    Args:
        db_path: Path to the database file
    
    Returns:
        bool: True if valid
    
    Raises:
        DatabaseValidationError: If validation fails
    """
    
    # 1. Check file exists
    if not os.path.exists(db_path):
        raise DatabaseValidationError("Database file not found.")
    
    # 2. Check file size
    file_size = os.path.getsize(db_path)
    
    if file_size < MIN_DB_SIZE:
        raise DatabaseValidationError("File is too small to be a valid SQLite database.")
    
    if file_size > MAX_DB_SIZE:
        raise DatabaseValidationError(
            f"Database file exceeds maximum size limit ({MAX_DB_SIZE // (1024*1024)} MB)."
        )
    
    # 3. Check SQLite magic bytes
    try:
        with open(db_path, "rb") as f:
            header = f.read(16)
            if not header.startswith(SQLITE_MAGIC):
                raise DatabaseValidationError(
                    "File is not a valid SQLite database (invalid header)."
                )
    except IOError as e:
        raise DatabaseValidationError(f"Failed to read database file: {str(e)}")
    
    # 4. Validate database integrity
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Run integrity check
        result = cursor.execute("PRAGMA integrity_check;").fetchone()
        if result[0] != "ok":
            raise DatabaseValidationError(
                f"Database integrity check failed: {result[0]}"
            )
        
        # Check that there are tables
        tables = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        ).fetchall()
        
        if not tables:
            raise DatabaseValidationError(
                "Database contains no tables."
            )
        
        # Validate each table is readable
        for (table,) in tables:
            try:
                cursor.execute(f'SELECT 1 FROM "{table}" LIMIT 1;')
            except sqlite3.Error as e:
                raise DatabaseValidationError(
                    f"Table '{table}' is corrupted or unreadable: {str(e)}"
                )
        
        conn.close()
        
    except sqlite3.Error as e:
        raise DatabaseValidationError(f"Database error: {str(e)}")
    
    return True


def get_database_info(db_path: str) -> dict:
    """
    Gets detailed information about a database.
    
    Args:
        db_path: Path to the database
    
    Returns:
        dict: Database information
    """
    
    validate_sqlite_db(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    info = {
        "file_size_bytes": os.path.getsize(db_path),
        "file_size_mb": round(os.path.getsize(db_path) / (1024 * 1024), 2),
        "tables": [],
        "total_rows": 0
    }
    
    # Get tables
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    ).fetchall()
    
    for (table,) in tables:
        try:
            row_count = cursor.execute(f'SELECT COUNT(*) FROM "{table}";').fetchone()[0]
            info["tables"].append({
                "name": table,
                "row_count": row_count
            })
            info["total_rows"] += row_count
        except:
            info["tables"].append({
                "name": table,
                "row_count": 0
            })
    
    # Get SQLite version
    version = cursor.execute("SELECT sqlite_version();").fetchone()[0]
    info["sqlite_version"] = version
    
    conn.close()
    
    return info


def check_dangerous_content(db_path: str) -> List[str]:
    """
    Checks for potentially dangerous content in the database.
    
    Args:
        db_path: Path to the database
    
    Returns:
        list: List of warnings (empty if safe)
    """
    
    warnings = []
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check for triggers (could contain malicious code)
        triggers = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger';"
        ).fetchall()
        
        if triggers:
            warnings.append(
                f"Database contains {len(triggers)} trigger(s). "
                "These will not be executed in read-only mode."
            )
        
        # Check for views with potentially complex queries
        views = cursor.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='view';"
        ).fetchall()
        
        if len(views) > 10:
            warnings.append(
                f"Database contains {len(views)} views. "
                "Complex views may slow down queries."
            )
        
        # Check for very large tables
        tables = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        ).fetchall()
        
        for (table,) in tables:
            try:
                count = cursor.execute(f'SELECT COUNT(*) FROM "{table}";').fetchone()[0]
                if count > 1000000:
                    warnings.append(
                        f"Table '{table}' contains over 1 million rows. "
                        "Queries may be slow."
                    )
            except:
                pass
        
        conn.close()
        
    except sqlite3.Error:
        pass
    
    return warnings
