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
        r"no such column: ([\w.]+)": "column_not_found",  # Matches table.column or column
        r"no such table: (\w+)": "table_not_found",
        r"ambiguous column name: (\w+)": "ambiguous_column",
        r"near ['\"]primary['\"]": "reserved_word_primary",
        r"near ['\"]([A-Za-z]+)['\"].*syntax error": "syntax_near_keyword",
        r"syntax error": "syntax_error",
        r"near \"(.+?)\": syntax error": "syntax_near",
        r"UNIQUE constraint failed": "unique_violation",
        r"GROUP BY clause": "group_by_needed",
        r"aggregate": "aggregate_error",
        r"datatype mismatch": "type_mismatch",
        r"SELECTExpected": "syntax_error",
        r"no such function": "function_not_found",
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
        
        return {
            "error_type": "unknown",
            "suggestion": "The query encountered an unexpected error.",
            "can_retry": False,
            "fix_hint": None
        }
    
    def _get_fix_for_error(self, error_type: str, captured: Optional[tuple], sql: str) -> Dict:
        """Generates fix suggestions for specific error types."""
        
        if error_type == "column_not_found":
            column = captured[0] if captured else "unknown"
            
            # Check if the column name looks like a table name (potential FK relationship error)
            # E.g., "t.Genre" where Track has GenreId, not Genre
            potential_table = None
            fk_hint = None
            
            # Extract table.column pattern from error (e.g., "t.Genre" → "Genre")
            column_name_only = column.split('.')[-1] if '.' in column else column
            
            # Check if column name matches a table name (case-insensitive)
            for table_name in self.all_tables:
                if column_name_only.lower() == table_name.lower():
                    potential_table = table_name
                    # Look for a foreign key column like "{table}Id"
                    fk_column = f"{table_name}Id"
                    if fk_column in self.all_columns:
                        fk_hint = f"Column '{column}' doesn't exist. Did you mean to JOIN with the {table_name} table? The relationship is through '{fk_column}'."
                    break
            
            if fk_hint:
                # This is likely a FK relationship error
                return {
                    "error_type": error_type,
                    "suggestion": fk_hint,
                    "can_retry": True,
                    "fix_hint": f"Need to JOIN with {potential_table} table using {fk_column}",
                    "requires_join": True,
                    "join_table": potential_table,
                    "replacement": None  # Don't do simple replacement, need full regeneration
                }
            
            # Otherwise, find similar column name
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
        
        elif error_type == "reserved_word_primary" or error_type == "syntax_near_keyword":
            keyword = captured[0] if captured else "reserved word"
            return {
                "error_type": error_type,
                "suggestion": f"Syntax error near reserved word or keyword '{keyword}'.",
                "can_retry": True,
                "fix_hint": "The query may be using a reserved word incorrectly or have a syntax issue. Will regenerate."
            }
        
        elif error_type == "function_not_found":
            return {
                "error_type": error_type,
                "suggestion": "SQL function not found or misspelled.",
                "can_retry": True,
                "fix_hint": "Regenerating with correct SQLite functions."
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
        column_lower = column.lower()
        for col in self.all_columns.keys():
            if col.lower() == column_lower:
                return col
        for col in self.all_columns.keys():
            if column_lower in col.lower() or col.lower() in column_lower:
                return col
        for col in self.all_columns.keys():
            if self._simple_similarity(column_lower, col.lower()) > 0.7:
                return col
        return None
    
    def _find_similar_table(self, table: str) -> Optional[str]:
        table_lower = table.lower()
        for t in self.all_tables:
            if t.lower() == table_lower:
                return t
        for t in self.all_tables:
            if table_lower in t.lower() or t.lower() in table_lower:
                return t
        return None
    
    def _simple_similarity(self, s1: str, s2: str) -> float:
        if not s1 or not s2: return 0.0
        common = set(s1) & set(s2)
        return len(common) / max(len(set(s1)), len(set(s2)))
    
    def apply_fix(self, sql: str, fix_info: Dict) -> Optional[str]:
        if not fix_info.get("can_retry"):
            return None
        
        error_type = fix_info.get("error_type")
        
        if error_type in ["column_not_found", "table_not_found"]:
            replacement = fix_info.get("replacement")
            if replacement:
                old, new = replacement
                return re.sub(rf'\b{re.escape(old)}\b', new, sql, flags=re.IGNORECASE)
        
        elif error_type == "syntax_near":
            suggestion = fix_info.get("suggestion", "")
            if "," in suggestion:
                # Fix trailing commas before keywords
                # e.g., "SELECT a, b, FROM t" -> "SELECT a, b FROM t"
                fixed_sql = re.sub(r',\s*(?=(?:FROM|WHERE|GROUP|ORDER|LIMIT|;|$))', ' ', sql, flags=re.IGNORECASE)
                if fixed_sql != sql:
                    return fixed_sql
        
        return None


def generate_retry_prompt(original_question: str, original_sql: str, error_message: str, fix_info: Dict, schema: Dict) -> str:
    # Enhanced schema display with foreign keys
    schema_lines = []
    for table, info in schema.items():
        columns_str = ', '.join(info.get('columns', []))
        schema_lines.append(f"Table {table}: {columns_str}")
        
        # Add foreign key information if available
        fks = info.get('foreign_keys', [])
        if fks:
            for fk in fks:
                schema_lines.append(f"  └─ FK: {fk.get('from')} → {fk.get('to_table')}.{fk.get('to_column')}")
    
    schema_text = "\n".join(schema_lines)
    
    # Add FK relationship hint if detected
    join_hint = ""
    if fix_info.get('requires_join'):
        join_table = fix_info.get('join_table', '')
        join_hint = f"\n\nIMPORTANT: You need to JOIN with the {join_table} table to access its columns."
    
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
{fix_info.get('fix_hint', 'Please try a different approach.')}{join_hint}

AVAILABLE SCHEMA:
{schema_text}

Please generate a corrected SQL query that:
1. Avoids the previous error
2. Uses only existing tables and columns
3. Properly qualifies ambiguous column names
4. Follows SQLite syntax
5. Uses proper JOINs when accessing related tables

REASONING:
<Explain your corrected approach>

SQL:
<Your corrected SQL query>
"""
