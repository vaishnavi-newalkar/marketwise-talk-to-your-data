"""
SQL Validator

Validates SQL queries for safety before execution.
Ensures only READ-ONLY operations are allowed.
"""

import re
from typing import Tuple, Optional


class SQLValidationError(Exception):
    """Raised when SQL validation fails."""
    pass


# Forbidden keywords that indicate write operations
FORBIDDEN_KEYWORDS = {
    # Data Manipulation
    "insert", "update", "delete", "replace", "upsert",
    # Schema Modification
    "drop", "alter", "truncate", "create", "rename",
    # Database Operations
    "attach", "detach", "reindex", "vacuum", "analyze",
    # Dangerous Functions
    "load_extension", "writefile", "readfile",
}

# Allowed statement starters
ALLOWED_STARTERS = {
    "select",
    "with",  # CTEs
    "pragma",  # Read-only pragmas only
    "explain",  # Query explanation
}

# Dangerous PRAGMA commands
DANGEROUS_PRAGMAS = {
    "pragma database_list",
    "pragma key",
    "pragma rekey", 
    "pragma journal_mode",
    "pragma locking_mode",
    "pragma synchronous",
    "pragma temp_store",
    "pragma cache_size",
    "pragma mmap_size",
    "pragma wal_checkpoint",
}


def validate_sql(sql: str) -> Tuple[bool, Optional[str]]:
    """
    Validates SQL for safety.
    
    Rules:
    - READ-ONLY queries only
    - Single statement only
    - No SQL comments (injection prevention)
    - No forbidden keywords
    - No dangerous PRAGMAs
    
    Args:
        sql: The SQL query to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    
    Raises:
        SQLValidationError: If validation fails
    """
    
    if not sql or not sql.strip():
        raise SQLValidationError("Empty SQL query.")
    
    # Normalize the SQL
    sql_clean = sql.strip()
    sql_lower = sql_clean.lower()
    
    # Remove extra whitespace for parsing
    sql_normalized = " ".join(sql_lower.split())
    
    # 1. Check for allowed statement starters
    starts_valid = any(sql_normalized.startswith(starter) for starter in ALLOWED_STARTERS)
    if not starts_valid:
        raise SQLValidationError(
            "Only SELECT, WITH (CTE), and read-only PRAGMA queries are allowed. "
            f"Query starts with: '{sql_lower[:20]}...'"
        )
    
    # 2. Check for multiple statements
    # Count semicolons (excluding those in strings)
    semicolon_count = count_semicolons_outside_strings(sql_clean)
    if semicolon_count > 1:
        raise SQLValidationError(
            "Multiple SQL statements are not allowed. "
            "Please submit one query at a time."
        )
    
    # 3. Block SQL comments (injection prevention)
    if has_sql_comments(sql_clean):
        raise SQLValidationError(
            "SQL comments (-- or /* */) are not allowed for security reasons."
        )
    
    # 4. Check for forbidden keywords
    for keyword in FORBIDDEN_KEYWORDS:
        # Use word boundary matching to avoid false positives
        pattern = rf'\b{keyword}\b'
        if re.search(pattern, sql_lower):
            raise SQLValidationError(
                f"Forbidden SQL operation detected: {keyword.upper()}. "
                "Only SELECT queries are allowed."
            )
    
    # 5. Check for dangerous PRAGMAs
    if sql_normalized.startswith("pragma"):
        for dangerous in DANGEROUS_PRAGMAS:
            if dangerous in sql_normalized:
                raise SQLValidationError(
                    f"This PRAGMA command is not allowed: {dangerous}"
                )
    
    # 6. Check for system table access
    system_patterns = [
        r'\bsqlite_master\b.*\bsql\b',  # Reading table creation SQL
        r'\battach\s+database\b',
        r'\bdetach\s+database\b',
    ]
    for pattern in system_patterns:
        if re.search(pattern, sql_lower):
            raise SQLValidationError(
                "Access to system tables or database operations is restricted."
            )
    
    # 7. Check for suspicious patterns
    suspicious_patterns = [
        (r';\s*--', "Statement followed by comment"),
        (r'union\s+all\s+select\s+null', "Suspicious UNION injection pattern"),
        (r"'\s*or\s+'1'\s*=\s*'1", "SQL injection pattern detected"),
        (r'"\s*or\s+"1"\s*=\s*"1', "SQL injection pattern detected"),
        (r'admin\s*--', "Suspicious comment pattern"),
        (r'\bexec\b', "EXEC command not allowed"),
        (r'\bexecute\b', "EXECUTE command not allowed"),
        (r'\bsp_', "Stored procedure calls not allowed"),
        (r'\bxp_', "Extended stored procedures not allowed"),
    ]
    
    for pattern, message in suspicious_patterns:
        if re.search(pattern, sql_lower):
            raise SQLValidationError(f"Suspicious pattern blocked: {message}")
    
    # 8. Validate CTE structure (WITH clause)
    if sql_normalized.startswith("with"):
        if not validate_cte_structure(sql_normalized):
            raise SQLValidationError(
                "Invalid CTE (WITH clause) structure. "
                "WITH must be followed by a valid SELECT statement."
            )
    
    return True, None


def count_semicolons_outside_strings(sql: str) -> int:
    """
    Counts semicolons that are not inside string literals.
    """
    count = 0
    in_single_quote = False
    in_double_quote = False
    prev_char = None
    
    for char in sql:
        if char == "'" and not in_double_quote and prev_char != "\\":
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote and prev_char != "\\":
            in_double_quote = not in_double_quote
        elif char == ";" and not in_single_quote and not in_double_quote:
            count += 1
        
        prev_char = char
    
    return count


def has_sql_comments(sql: str) -> bool:
    """
    Checks if SQL contains comments.
    """
    # Line comments: --
    if re.search(r'--(?!["\'])', sql):
        return True
    
    # Block comments: /* */
    if re.search(r'/\*|\*/', sql):
        return True
    
    return False



def validate_cte_structure(sql_lower: str) -> bool:
    """
    Validates that a WITH clause is properly structured.
    
    Valid CTE patterns:
    - WITH cte_name AS (SELECT ...) SELECT ...
    - WITH cte1 AS (...), cte2 AS (...) SELECT ...
    - WITH RECURSIVE cte AS (...) SELECT ...
    """
    # Must contain AS after WITH (as a whole word)
    if not re.search(r'\bas\b', sql_lower):
        return False
    
    # Must contain SELECT somewhere (as a whole word)
    if not re.search(r'\bselect\b', sql_lower):
        return False
    
    # Check for valid CTE pattern: WITH ... AS (...) SELECT
    # The pattern should be: WITH [RECURSIVE] name AS (subquery) main_query
    
    # Find positions of key keywords
    with_match = re.search(r'\bwith\b', sql_lower)
    if not with_match:
        return False
    with_pos = with_match.start()
    
    # Look for AS after WITH (must be a word)
    as_match = re.search(r'\bas\b', sql_lower[with_pos:])
    if not as_match:
        return False
    as_pos = with_pos + as_match.start()

    
    # Look for opening parenthesis after AS
    paren_open = sql_lower.find("(", as_pos)
    if paren_open == -1:
        return False
    
    # Find the matching closing parenthesis
    paren_count = 0
    paren_close = -1
    for i in range(paren_open, len(sql_lower)):
        if sql_lower[i] == "(":
            paren_count += 1
        elif sql_lower[i] == ")":
            paren_count -= 1
            if paren_count == 0:
                paren_close = i
                break
    
    if paren_close == -1:
        return False
    
    # After the closing paren, there should be either:
    # 1. Another CTE: comma followed by identifier AS (...)
    # 2. Final SELECT statement
    remaining = sql_lower[paren_close + 1:].strip()
    
    # Check if there's a SELECT after the CTE(s)
    if re.search(r'\bselect\b', remaining):
        return True
    
    # Check if there's another CTE (comma followed by more CTEs)
    if remaining.startswith(","):
        # Multiple CTEs - check if there's a SELECT after the last one
        return bool(re.search(r'\bselect\b', sql_lower[paren_close:]))

    
    return False



def sanitize_identifiers(sql: str, allowed_tables: list, allowed_columns: list) -> Tuple[bool, str]:
    """
    Validates that SQL only references allowed tables and columns.
    
    Note: This is a best-effort check and may have false positives/negatives.
    
    Args:
        sql: The SQL query
        allowed_tables: List of allowed table names
        allowed_columns: List of allowed column names
    
    Returns:
        Tuple of (is_valid, error_message or empty string)
    """
    
    sql_lower = sql.lower()
    
    # Extract identifiers (simplified)
    # This is a basic check and won't catch all cases
    identifiers = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', sql_lower)
    
    # SQL keywords to ignore
    sql_keywords = {
        'select', 'from', 'where', 'and', 'or', 'not', 'in', 'is', 'null',
        'like', 'between', 'join', 'inner', 'outer', 'left', 'right', 'on',
        'as', 'order', 'by', 'asc', 'desc', 'limit', 'offset', 'group',
        'having', 'distinct', 'count', 'sum', 'avg', 'min', 'max', 'case',
        'when', 'then', 'else', 'end', 'with', 'union', 'all', 'except',
        'intersect', 'exists', 'true', 'false', 'cast', 'coalesce', 'nullif',
        'ifnull', 'typeof', 'length', 'substr', 'upper', 'lower', 'trim',
        'replace', 'instr', 'abs', 'round', 'date', 'time', 'datetime',
        'strftime', 'julianday', 'over', 'partition', 'row_number', 'rank',
        'dense_rank', 'lag', 'lead', 'first_value', 'last_value', 'recursive'
    }
    
    allowed_lower = {t.lower() for t in allowed_tables} | {c.lower() for c in allowed_columns}
    
    unknown = []
    for ident in identifiers:
        if ident not in sql_keywords and ident not in allowed_lower:
            if not ident.isdigit():
                unknown.append(ident)
    
    if unknown:
        return False, f"Unknown identifiers: {', '.join(set(unknown)[:5])}"
    
    return True, ""


def get_query_complexity(sql: str) -> int:
    """
    Estimates query complexity on a scale of 1-10.
    
    Higher complexity = more expensive query.
    """
    
    sql_lower = sql.lower()
    complexity = 1
    
    # Count JOINs
    join_count = len(re.findall(r'\bjoin\b', sql_lower))
    complexity += min(join_count, 3)
    
    # Count subqueries
    subquery_count = len(re.findall(r'\(\s*select\b', sql_lower))
    complexity += min(subquery_count * 2, 4)
    
    # Count aggregations
    agg_count = len(re.findall(r'\b(count|sum|avg|min|max)\s*\(', sql_lower))
    complexity += min(agg_count, 2)
    
    # Check for GROUP BY
    if re.search(r'\bgroup\s+by\b', sql_lower):
        complexity += 1
    
    # Check for ORDER BY
    if re.search(r'\border\s+by\b', sql_lower):
        complexity += 1
    
    # Check for DISTINCT
    if re.search(r'\bdistinct\b', sql_lower):
        complexity += 1
    
    # Check for UNION
    if re.search(r'\bunion\b', sql_lower):
        complexity += 2
    
    return min(complexity, 10)
