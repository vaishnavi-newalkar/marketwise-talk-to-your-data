"""
SQL Executor with enhanced result handling.
Executes queries in READ-ONLY mode for safety.
"""

import sqlite3


class SQLExecutionError(Exception):
    """Raised when SQL execution fails."""
    pass


def execute_sql(db_path: str, sql: str, max_rows: int = 1000) -> dict:
    """
    Executes a SQL query against the database.
    
    Args:
        db_path: Path to SQLite database
        sql: SQL query to execute
        max_rows: Maximum rows to return (safety limit)
    
    Returns:
        dict: {
            "columns": list[str],     # Column names
            "rows": list[list],       # Row data
            "row_count": int,         # Total rows returned
            "truncated": bool         # True if results were truncated
        }
    
    Raises:
        SQLExecutionError: If query fails
    """
    
    if not sql or not sql.strip():
        raise SQLExecutionError("Empty SQL query provided.")
    
    try:
        # Open in read-only mode using URI
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Execute the query
        cursor.execute(sql)
        
        # Get column names
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        
        # Fetch rows with limit
        all_rows = cursor.fetchmany(max_rows + 1)
        truncated = len(all_rows) > max_rows
        
        if truncated:
            rows = all_rows[:max_rows]
        else:
            rows = all_rows
        
        # Convert sqlite3.Row to list for serialization
        rows_as_lists = [list(row) for row in rows]
        
        conn.close()
        
        return {
            "columns": columns,
            "rows": rows_as_lists,
            "row_count": len(rows_as_lists),
            "truncated": truncated
        }
        
    except sqlite3.OperationalError as e:
        raise SQLExecutionError(f"SQL execution failed: {str(e)}")
    except sqlite3.DatabaseError as e:
        raise SQLExecutionError(f"Database error: {str(e)}")
    except Exception as e:
        raise SQLExecutionError(f"Unexpected error: {str(e)}")


def execute_sql_simple(db_path: str, sql: str) -> list:
    """
    Simple execution that returns raw tuples.
    For backward compatibility.
    """
    result = execute_sql(db_path, sql)
    return [tuple(row) for row in result["rows"]]
