"""
Self-Correction Module

Handles query failures and retries with alternative approaches.
Implements the "think, explore, validate, and recover from mistakes" paradigm.
"""

import re
from typing import Dict, Optional, List, Tuple


class QueryCorrector:
    """
    Handles SQL query failures and generates corrected queries.
    """
    
    MAX_RETRIES = 2
    
    # Common error patterns and their fixes
    ERROR_PATTERNS = {
        r"no such column: (\w+)": "column_not_found",
        r"no such table: (\w+)": "table_not_found",
        r"ambiguous column name: (\w+)": "ambiguous_column",
        r"syntax error": "syntax_error",
        r"near \"(\w+)\": syntax error": "syntax_near",
        r"UNIQUE constraint failed": "unique_violation",
        r"GROUP BY clause": "group_by_needed",
        r"aggregate": "aggregate_error",
        r"datatype mismatch": "type_mismatch",
    }
    
    def __init__(self, schema: Dict):
        self.schema = schema
        self.all_columns = self._extract_all_columns()
        self.all_tables = list(schema.keys())
    
    def _extract_all_columns(self) -> Dict[str, List[str]]:
        """Extracts all columns mapped to their tables."""
        columns = {}
        for table, info in self.schema.items():
            for col in info.get("columns", []):
                if col not in columns:
                    columns[col] = []
                columns[col].append(table)
        return columns
    
    def analyze_error(self, error_message: str, sql: str) -> Dict:
        """
        Analyzes an error and suggests corrections.
        
        Args:
            error_message: The error message from SQL execution
            sql: The SQL that failed
        
        Returns:
            dict with 'error_type', 'suggestion', 'can_retry', 'fix_hint'
        """
        
        error_lower = error_message.lower()
        
        for pattern, error_type in self.ERROR_PATTERNS.items():
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                return self._get_fix_for_error(
                    error_type, 
                    match.groups() if match.groups() else None,
                    sql
                )
        
        # Unknown error
        return {
            "error_type": "unknown",
            "suggestion": "The query encountered an unexpected error.",
            "can_retry": False,
            "fix_hint": None
        }
    
    def _get_fix_for_error(
        self, 
        error_type: str, 
        captured: Optional[tuple],
        sql: str
    ) -> Dict:
        """Generates fix suggestions for specific error types."""
        
        if error_type == "column_not_found":
            column = captured[0] if captured else "unknown"
            similar = self._find_similar_column(column)
            
            return {
                "error_type": error_type,
                "suggestion": f"Column '{column}' doesn't exist.",
                "can_retry": bool(similar),
                "fix_hint": f"Did you mean '{similar}'?" if similar else None,
                "replacement": (column, similar) if similar else None
            }
        
        elif error_type == "table_not_found":
            table = captured[0] if captured else "unknown"
            similar = self._find_similar_table(table)
            
            return {
                "error_type": error_type,
                "suggestion": f"Table '{table}' doesn't exist.",
                "can_retry": bool(similar),
                "fix_hint": f"Did you mean '{similar}'?" if similar else None,
                "replacement": (table, similar) if similar else None
            }
        
        elif error_type == "ambiguous_column":
            column = captured[0] if captured else "unknown"
            tables = self.all_columns.get(column, [])
            
            return {
                "error_type": error_type,
                "suggestion": f"Column '{column}' exists in multiple tables: {', '.join(tables)}",
                "can_retry": True,
                "fix_hint": f"Qualify with table name: {tables[0]}.{column}" if tables else None,
                "tables_with_column": tables
            }
        
        elif error_type == "syntax_error" or error_type == "syntax_near":
            keyword = captured[0] if captured else None
            
            return {
                "error_type": error_type,
                "suggestion": f"SQL syntax error near '{keyword}'." if keyword else "SQL syntax error.",
                "can_retry": True,
                "fix_hint": "Regenerating query with corrected syntax."
            }
        
        elif error_type == "group_by_needed":
            return {
                "error_type": error_type,
                "suggestion": "Aggregate function used without GROUP BY.",
                "can_retry": True,
                "fix_hint": "Adding GROUP BY clause for non-aggregated columns."
            }
        
        elif error_type == "type_mismatch":
            return {
                "error_type": error_type,
                "suggestion": "Data type mismatch in comparison.",
                "can_retry": True,
                "fix_hint": "Adjusting data types in the query."
            }
        
        return {
            "error_type": error_type,
            "suggestion": "Query error occurred.",
            "can_retry": False,
            "fix_hint": None
        }
    
    def _find_similar_column(self, column: str) -> Optional[str]:
        """Finds a similar column name using fuzzy matching."""
        column_lower = column.lower()
        
        # Exact match (different case)
        for col in self.all_columns.keys():
            if col.lower() == column_lower:
                return col
        
        # Partial match
        for col in self.all_columns.keys():
            if column_lower in col.lower() or col.lower() in column_lower:
                return col
        
        # Levenshtein-like simple matching
        for col in self.all_columns.keys():
            if self._simple_similarity(column_lower, col.lower()) > 0.7:
                return col
        
        return None
    
    def _find_similar_table(self, table: str) -> Optional[str]:
        """Finds a similar table name."""
        table_lower = table.lower()
        
        for t in self.all_tables:
            if t.lower() == table_lower:
                return t
        
        for t in self.all_tables:
            if table_lower in t.lower() or t.lower() in table_lower:
                return t
        
        return None
    
    def _simple_similarity(self, s1: str, s2: str) -> float:
        """Simple similarity score based on common characters."""
        if not s1 or not s2:
            return 0.0
        
        common = set(s1) & set(s2)
        return len(common) / max(len(set(s1)), len(set(s2)))
    
    def apply_fix(self, sql: str, fix_info: Dict) -> Optional[str]:
        """
        Applies a fix to the SQL query.
        
        Args:
            sql: Original SQL
            fix_info: Fix information from analyze_error
        
        Returns:
            Corrected SQL or None if fix cannot be applied
        """
        
        if not fix_info.get("can_retry"):
            return None
        
        error_type = fix_info.get("error_type")
        
        if error_type in ["column_not_found", "table_not_found"]:
            replacement = fix_info.get("replacement")
            if replacement:
                old, new = replacement
                return re.sub(
                    rf'\b{re.escape(old)}\b', 
                    new, 
                    sql, 
                    flags=re.IGNORECASE
                )
        
        elif error_type == "ambiguous_column":
            tables = fix_info.get("tables_with_column", [])
            if tables:
                # This is a hint for regeneration, not a direct fix
                return None
        
        return None


def generate_retry_prompt(
    original_question: str,
    original_sql: str,
    error_message: str,
    fix_info: Dict,
    schema: Dict
) -> str:
    """
    Generates a prompt for retrying SQL generation.
    
    Args:
        original_question: User's original question
        original_sql: SQL that failed
        error_message: Error message
        fix_info: Fix information
        schema: Database schema
    
    Returns:
        Prompt for LLM to regenerate SQL
    """
    
    schema_text = "\n".join([
        f"Table {table}: {', '.join(info.get('columns', []))}"
        for table, info in schema.items()
    ])
    
    return f"""The previous SQL query failed. Please generate a corrected query.

ORIGINAL QUESTION:
{original_question}

PREVIOUS SQL (FAILED):
{original_sql}

ERROR:
{error_message}

ANALYSIS:
{fix_info.get('suggestion', 'Unknown error')}

HINT:
{fix_info.get('fix_hint', 'Please try a different approach.')}

AVAILABLE SCHEMA:
{schema_text}

Please generate a corrected SQL query that:
1. Avoids the previous error
2. Uses only existing tables and columns
3. Properly qualifies ambiguous column names
4. Follows SQLite syntax

REASONING:
<Explain your corrected approach>

SQL:
<Your corrected SQL query>
"""


def build_retry_context(
    attempts: List[Dict],
    max_context: int = 2
) -> str:
    """
    Builds context from previous failed attempts.
    
    Args:
        attempts: List of previous attempt info
        max_context: Maximum attempts to include
    
    Returns:
        Context string for LLM
    """
    
    recent = attempts[-max_context:] if len(attempts) > max_context else attempts
    
    lines = ["Previous attempts that failed:"]
    for i, attempt in enumerate(recent, 1):
        lines.append(f"\nAttempt {i}:")
        lines.append(f"  SQL: {attempt.get('sql', 'N/A')[:100]}...")
        lines.append(f"  Error: {attempt.get('error', 'Unknown')}")
    
    lines.append("\nPlease avoid these mistakes in your new query.")
    
    return "\n".join(lines)
